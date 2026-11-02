// The Last Skyfarer: Piko, Kieran's companion (GDD 5).

#include "PikoCompanion.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"
#include "GliderComponent.h"
#include "WindVolume.h"

APikoCompanion::APikoCompanion()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostPhysics;

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	RootComponent = Body;
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetRelativeScale3D(FVector(0.35f));

	// Placeholder until Piko's model exists: a sphere.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (Sphere.Succeeded())
	{
		Body->SetStaticMesh(Sphere.Object);
	}
}

void APikoCompanion::BeginPlay()
{
	Super::BeginPlay();
	if (!FollowTarget)
	{
		FollowTarget = UGameplayStatics::GetPlayerCharacter(this, 0);
	}
	if (Body->GetMaterial(0))
	{
		BodyMaterial = Body->CreateAndSetMaterialInstanceDynamic(0);
	}
	if (FollowTarget)
	{
		SetActorLocation(GetDesiredLocation());
	}
}

FVector APikoCompanion::GetDesiredLocation() const
{
	if (!FollowTarget)
	{
		return GetActorLocation();
	}
	EPikoPerch Effective = Perch;
	if (const UGliderComponent* Glider = FollowTarget->FindComponentByClass<UGliderComponent>())
	{
		if (Glider->IsGliding())
		{
			Effective = EPikoPerch::GliderBar;
		}
	}
	const FVector* Offset = &FollowOffset;
	switch (Effective)
	{
	case EPikoPerch::Shoulder: Offset = &ShoulderOffset; break;
	case EPikoPerch::GliderBar: Offset = &GliderBarOffset; break;
	case EPikoPerch::Satchel: Offset = &SatchelOffset; break;
	default: break;
	}
	return FollowTarget->GetActorTransform().TransformPosition(*Offset);
}

int32 APikoCompanion::Sense()
{
	UWindSubsystem* Wind = GetWorld() ? GetWorld()->GetSubsystem<UWindSubsystem>() : nullptr;
	if (!Wind)
	{
		return 0;
	}
	const FVector Here = GetActorLocation();
	const float Nearest = Wind->DistanceToNearestHidden(Here);
	const float Proximity = Nearest < GlowRange ? 1.f - FMath::Clamp(Nearest / GlowRange, 0.f, 1.f) : 0.f;

	const int32 Revealed = Wind->RevealHiddenNear(Here, SenseRange);
	if (Revealed > 0)
	{
		RevealPulse = 1.f;
		OnSensedCurrent.Broadcast(Revealed);
	}
	MarkingGlow = FMath::Max(Proximity, RevealPulse);
	if (BodyMaterial)
	{
		BodyMaterial->SetScalarParameterValue(MarkingGlowParam, MarkingGlow);
	}
	return Revealed;
}

void APikoCompanion::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!FollowTarget)
	{
		FollowTarget = UGameplayStatics::GetPlayerCharacter(this, 0);
		if (!FollowTarget)
		{
			return;
		}
	}

	// Critically damped spring toward the perch point.
	const FVector Target = GetDesiredLocation();
	FVector Pos = GetActorLocation();
	if (FVector::Dist(Pos, Target) > TeleportDistance)
	{
		Pos = Target;
		Velocity = FVector::ZeroVector;
	}
	else
	{
		const float W = SpringStiffness;
		const FVector Accel = (Target - Pos) * (W * W) - Velocity * (2.f * W);
		Velocity += Accel * DeltaSeconds;
		Pos += Velocity * DeltaSeconds;
	}

	// Gentle idle bob, only while floating.
	BobTime += DeltaSeconds;
	const bool bFloating = Perch == EPikoPerch::Follow;
	const FVector Bob = bFloating ? FVector(0.f, 0.f, BobAmplitude * FMath::Sin(BobTime * BobFrequency * 2.f * PI)) : FVector::ZeroVector;
	SetActorLocation(Pos + Bob);
	SetActorRotation(FRotator(0.f, FollowTarget->GetActorRotation().Yaw, 0.f));

	RevealPulse = FMath::Max(0.f, RevealPulse - DeltaSeconds * 0.5f);
	SenseTimer -= DeltaSeconds;
	if (SenseTimer <= 0.f)
	{
		SenseTimer = SenseInterval;
		Sense();
	}
}

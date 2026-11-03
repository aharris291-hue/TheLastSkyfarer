// The Last Skyfarer: wind currents, updrafts and crosswinds (GDD 2.2).

#include "WindVolume.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "UObject/ConstructorHelpers.h"

AWindVolume::AWindVolume()
{
	PrimaryActorTick.bCanEverTick = false;

	Spline = CreateDefaultSubobject<USplineComponent>(TEXT("Spline"));
	RootComponent = Spline;
	Spline->SetMobility(EComponentMobility::Static);

	Visual = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Visual"));
	Visual->SetupAttachment(Spline);
	Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Visual->SetCastShadow(false);
	Visual->SetMobility(EComponentMobility::Static);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (Sphere.Succeeded())
	{
		Visual->SetStaticMesh(Sphere.Object);
	}
}

void AWindVolume::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	RebuildVisual();
}

void AWindVolume::BeginPlay()
{
	Super::BeginPlay();
	if (UWindSubsystem* Sub = GetWorld() ? GetWorld()->GetSubsystem<UWindSubsystem>() : nullptr)
	{
		Sub->Register(this);
	}
	RebuildVisual();
}

void AWindVolume::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UWindSubsystem* Sub = GetWorld() ? GetWorld()->GetSubsystem<UWindSubsystem>() : nullptr)
	{
		Sub->Unregister(this);
	}
	Super::EndPlay(Reason);
}

void AWindVolume::Reveal()
{
	if (!bRevealed)
	{
		bRevealed = true;
		UpdateVisibility();
	}
}

float AWindVolume::DistanceToSpline(const FVector& WorldLocation) const
{
	const FVector Closest = Spline->FindLocationClosestToWorldLocation(WorldLocation, ESplineCoordinateSpace::World);
	return FVector::Dist(Closest, WorldLocation);
}

FWindSample AWindVolume::SampleWind(const FVector& WorldLocation) const
{
	FWindSample Out;
	if (!IsActive())
	{
		return Out;
	}

	const float InputKey = Spline->FindInputKeyClosestToWorldLocation(WorldLocation);
	const FVector Closest = Spline->GetLocationAtSplineInputKey(InputKey, ESplineCoordinateSpace::World);
	const float Dist = FVector::Dist(Closest, WorldLocation);
	if (Dist > Radius)
	{
		return Out;
	}

	// Past the ends of an open spline the wind stops.
	const float LastKey = static_cast<float>(Spline->GetNumberOfSplinePoints() - 1);
	if (!Spline->IsClosedLoop() && (InputKey <= KINDA_SMALL_NUMBER || InputKey >= LastKey - KINDA_SMALL_NUMBER))
	{
		const FVector EndPoint = Spline->GetLocationAtSplineInputKey(InputKey, ESplineCoordinateSpace::World);
		const FVector EndTangent = Spline->GetDirectionAtSplineInputKey(InputKey, ESplineCoordinateSpace::World);
		const float Along = FVector::DotProduct(WorldLocation - EndPoint, EndTangent);
		if ((InputKey <= KINDA_SMALL_NUMBER && Along < -1.f) || (InputKey > KINDA_SMALL_NUMBER && Along > 1.f))
		{
			return Out;
		}
	}

	const float Alpha = Dist / FMath::Max(Radius, 1.f);
	const float Scale = FMath::Lerp(1.f, EdgeFalloff, Alpha);
	const float SpeedCm = Strength * 100.f * Scale;

	Out.bInside = true;
	switch (WindType)
	{
	case EWindVolumeType::Current:
		Out.Velocity = Spline->GetDirectionAtSplineInputKey(InputKey, ESplineCoordinateSpace::World) * SpeedCm;
		Out.bHoldAltitude = true;
		break;
	case EWindVolumeType::Updraft:
		Out.Velocity = FVector::UpVector * SpeedCm;
		break;
	case EWindVolumeType::Crosswind:
		Out.Velocity = GetActorRightVector() * SpeedCm;
		break;
	}
	return Out;
}

void AWindVolume::RebuildVisual()
{
	if (!Visual)
	{
		return;
	}
	Visual->ClearInstances();
	const float Length = Spline->GetSplineLength();
	const int32 Count = FMath::Clamp(FMath::FloorToInt(Length / FMath::Max(BeadSpacing, 50.f)) + 1, 2, 400);
	const float BeadScale = WindType == EWindVolumeType::Updraft ? 0.6f : 0.4f;
	for (int32 i = 0; i < Count; ++i)
	{
		const float D = Length * i / (Count - 1);
		const FVector Loc = Spline->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::Local);
		Visual->AddInstance(FTransform(FRotator::ZeroRotator, Loc, FVector(BeadScale)));
	}
	UpdateVisibility();
}

void AWindVolume::UpdateVisibility()
{
	if (Visual)
	{
		Visual->SetVisibility(IsActive());
		Visual->SetHiddenInGame(!IsActive());
	}
}

FWindSample UWindSubsystem::SampleWind(const FVector& WorldLocation) const
{
	FWindSample Sum;
	for (const TWeakObjectPtr<AWindVolume>& Weak : Volumes)
	{
		if (const AWindVolume* V = Weak.Get())
		{
			const FWindSample S = V->SampleWind(WorldLocation);
			if (S.bInside)
			{
				Sum.Velocity += S.Velocity;
				Sum.bHoldAltitude |= S.bHoldAltitude;
				Sum.bInside = true;
			}
		}
	}
	return Sum;
}

int32 UWindSubsystem::RevealHiddenNear(const FVector& WorldLocation, float Range)
{
	int32 Revealed = 0;
	for (const TWeakObjectPtr<AWindVolume>& Weak : Volumes)
	{
		AWindVolume* V = Weak.Get();
		if (V && V->bStartsHidden && !V->IsRevealed() && V->DistanceToSpline(WorldLocation) <= Range)
		{
			V->Reveal();
			++Revealed;
		}
	}
	return Revealed;
}

float UWindSubsystem::DistanceToNearestHidden(const FVector& WorldLocation) const
{
	float Best = TNumericLimits<float>::Max();
	for (const TWeakObjectPtr<AWindVolume>& Weak : Volumes)
	{
		const AWindVolume* V = Weak.Get();
		if (V && V->bStartsHidden && !V->IsRevealed())
		{
			Best = FMath::Min(Best, V->DistanceToSpline(WorldLocation));
		}
	}
	return Best;
}

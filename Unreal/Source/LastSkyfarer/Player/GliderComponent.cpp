// The Last Skyfarer: the Ancient Glider (GDD 2).

#include "GliderComponent.h"

#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "WindVolume.h"

UGliderComponent::UGliderComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

void UGliderComponent::BeginPlay()
{
	Super::BeginPlay();
	Character = Cast<ACharacter>(GetOwner());
}

bool UGliderComponent::IsNearGround(float Distance, FHitResult& OutHit) const
{
	if (!Character)
	{
		return false;
	}
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	const FVector Start = Character->GetActorLocation();
	const FVector End = Start - FVector(0.f, 0.f, Capsule->GetScaledCapsuleHalfHeight() + Distance);
	FCollisionQueryParams Query(SCENE_QUERY_STAT(GliderGround), false, Character);
	return GetWorld()->SweepSingleByChannel(OutHit, Start, End, FQuat::Identity, ECC_Visibility,
		FCollisionShape::MakeSphere(Capsule->GetScaledCapsuleRadius() * 0.9f), Query);
}

bool UGliderComponent::TryDeploy()
{
	if (!bHasGlider || bGliding || !Character)
	{
		return false;
	}
	UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	if (!Move || !Move->IsFalling())
	{
		return false;
	}
	FHitResult Hit;
	if (IsNearGround(MinDeployHeight, Hit))
	{
		return false;
	}

	State = FGliderModel::FromVelocity(Move->Velocity / 100.f, Params);
	if (Move->Velocity.Size2D() < 10.f)
	{
		State.Yaw = Character->GetActorRotation().Yaw;
	}
	Input = FGliderInput();
	bGliding = true;
	Move->SetMovementMode(MOVE_Flying);
	OnDeployed.Broadcast();
	return true;
}

void UGliderComponent::Stow()
{
	if (!bGliding)
	{
		return;
	}
	bGliding = false;
	if (Character)
	{
		if (UCharacterMovementComponent* Move = Character->GetCharacterMovement())
		{
			Move->SetMovementMode(MOVE_Falling);
		}
	}
}

void UGliderComponent::Land(float ImpactSpeed)
{
	const bool bRoll = FGliderModel::IsRollLanding(ImpactSpeed, Params);
	bGliding = false;
	if (UCharacterMovementComponent* Move = Character->GetCharacterMovement())
	{
		Move->Velocity.Z = 0.f;
		Move->SetMovementMode(MOVE_Walking);
		if (bRoll)
		{
			Move->Velocity *= 0.3f;
			if (AController* C = Character->GetController())
			{
				C->SetIgnoreMoveInput(true);
				FTimerHandle Handle;
				TWeakObjectPtr<AController> WeakC(C);
				GetWorld()->GetTimerManager().SetTimer(Handle, [WeakC]()
				{
					if (WeakC.IsValid())
					{
						WeakC->SetIgnoreMoveInput(false);
					}
				}, RollLandingStagger, false);
			}
		}
	}
	OnLanded.Broadcast(bRoll);
}

void UGliderComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (!bGliding || !Character)
	{
		return;
	}
	UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	if (!Move || Move->MovementMode != MOVE_Flying)
	{
		bGliding = false;
		return;
	}

	FGliderInput StepInput = Input;
	StepInput.bAssist = bAssistMode;
	const FGliderStepResult Step = FGliderModel::Step(State, StepInput, Params, DeltaTime);

	FVector Velocity = Step.AirDisplacement * 100.f / DeltaTime;

	if (const UWindSubsystem* Wind = GetWorld()->GetSubsystem<UWindSubsystem>())
	{
		const FWindSample W = Wind->SampleWind(Character->GetActorLocation());
		if (W.bInside)
		{
			Velocity += W.Velocity;
			if (W.bHoldAltitude && Velocity.Z < 0.f)
			{
				Velocity.Z = 0.f;
			}
		}
	}

	Move->Velocity = Velocity;
	Character->SetActorRotation(FRotator(0.f, State.Yaw, 0.f));

	FHitResult Hit;
	if (Velocity.Z <= 0.f && IsNearGround(25.f, Hit) && Hit.ImpactNormal.Z >= Move->GetWalkableFloorZ())
	{
		Land(State.Speed);
	}
}

#include "LSCompassComponent.h"

#include "Components/SplineComponent.h"
#include "LSMapMarkerComponent.h"
#include "LSStorySubsystem.h"
#include "WindVolume.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

ULSCompassComponent::ULSCompassComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

bool ULSCompassComponent::IsUnlocked() const
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	return Story && (UnlockFlag.IsNone() || Story->HasFlag(UnlockFlag));
}

void ULSCompassComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	CooldownLeft = FMath::Max(0.f, CooldownLeft - DeltaTime);
}

void ULSCompassComponent::Aim(FLSCompassReading& Reading, const FVector& From, const FVector& Facing, const FVector& Target)
{
	Reading.bHasTarget = true;
	Reading.Target = Target;
	const FVector Flat = FVector(Target.X - From.X, Target.Y - From.Y, 0.f);
	Reading.Distance = (Target - From).Size();
	Reading.Direction = Flat.GetSafeNormal();
	const FVector Face = FVector(Facing.X, Facing.Y, 0.f).GetSafeNormal();
	if (Reading.Direction.IsNearlyZero() || Face.IsNearlyZero())
	{
		Reading.RelativeYaw = 0.f;
		return;
	}
	Reading.RelativeYaw = FMath::FindDeltaAngleDegrees(Face.Rotation().Yaw, Reading.Direction.Rotation().Yaw);
}

FLSCompassReading ULSCompassComponent::Read(const ULSStorySubsystem& Story, const ULSMapSubsystem* Map, const UWindSubsystem* Wind,
	const FVector& From, const FVector& Facing, float Range)
{
	FLSCompassReading Reading;

	// Impossible routes first: a hidden current nearby always wins (GDD 3).
	if (Wind)
	{
		float Best = Range;
		FVector BestPoint;
		for (const TWeakObjectPtr<AWindVolume>& Weak : Wind->GetVolumes())
		{
			const AWindVolume* V = Weak.Get();
			if (!V || !V->bStartsHidden || V->IsRevealed() || !V->Spline) continue;
			const FVector P = V->Spline->FindLocationClosestToWorldLocation(From, ESplineCoordinateSpace::World);
			const float D = FVector::Dist(From, P);
			if (D < Best) { Best = D; BestPoint = P; }
		}
		if (Best < Range)
		{
			Aim(Reading, From, Facing, BestPoint);
			Reading.bImpossibleRoute = true;
			return Reading;
		}
	}

	FVector Target;
	if (Map && Map->FindCompassTarget(Story, From, Target))
	{
		Aim(Reading, From, Facing, Target);
	}
	return Reading;
}

bool ULSCompassComponent::Pulse()
{
	if (!IsUnlocked() || !IsReady()) return false;
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	const AActor* Owner = GetOwner();
	UWorld* World = GetWorld();
	if (!Story || !Owner || !World) return false;

	CooldownLeft = Cooldown;
	const FLSCompassReading Reading = Read(*Story, World->GetSubsystem<ULSMapSubsystem>(), World->GetSubsystem<UWindSubsystem>(),
		Owner->GetActorLocation(), Owner->GetActorForwardVector(), ImpossibleRouteRange);
	OnPulse.Broadcast(Reading);
	return true;
}

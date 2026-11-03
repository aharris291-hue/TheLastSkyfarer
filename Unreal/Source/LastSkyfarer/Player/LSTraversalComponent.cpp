// The Last Skyfarer: mantle, ledge hang and shimmy, and climbing (GDD 1).

#include "LSTraversalComponent.h"

#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
	bool IsWall(const FHitResult& Hit)
	{
		return Hit.bBlockingHit && FMath::Abs(Hit.ImpactNormal.Z) < 0.3f;
	}

	FVector Horizontal(const FVector& V)
	{
		return FVector(V.X, V.Y, 0.f).GetSafeNormal();
	}
}

ULSTraversalComponent::ULSTraversalComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

void ULSTraversalComponent::BeginPlay()
{
	Super::BeginPlay();
	Character = Cast<ACharacter>(GetOwner());
}

double ULSTraversalComponent::Now() const
{
	return GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
}

float ULSTraversalComponent::FeetZ() const
{
	return Character->GetActorLocation().Z - Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
}

void ULSTraversalComponent::SetMoveInput(const FVector& WorldDirection, float Right, float Forward)
{
	MoveDir = Horizontal(WorldDirection);
	StickRight = Right;
	StickForward = Forward;
}

bool ULSTraversalComponent::TraceWall(const FVector& From, const FVector& Direction, FHitResult& Hit) const
{
	const float Radius = Character->GetCapsuleComponent()->GetScaledCapsuleRadius();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(TraversalWall), false, Character);
	return GetWorld()->LineTraceSingleByChannel(Hit, From, From + Direction * (Radius + WallReach), ECC_Visibility, Params) && IsWall(Hit);
}

bool ULSTraversalComponent::CapsuleFits(const FVector& Location) const
{
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(TraversalRoom), false, Character);
	return !GetWorld()->OverlapBlockingTestByChannel(Location, FQuat::Identity, ECC_Pawn,
		FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius() * 0.95f, Capsule->GetScaledCapsuleHalfHeight() * 0.95f), Params);
}

bool ULSTraversalComponent::FindLedge(const FVector& Direction, FLSLedge& Out) const
{
	Out = FLSLedge();
	if (!Character)
	{
		return false;
	}
	const FVector Dir = Horizontal(Direction);
	if (Dir.IsNearlyZero())
	{
		return false;
	}
	const FVector Loc = Character->GetActorLocation();
	const float Feet = FeetZ();
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();

	// Find a wall at knee, chest or head height.
	FHitResult Wall;
	bool bWall = false;
	for (const float Z : { 40.f, 100.f, 160.f })
	{
		if (TraceWall(FVector(Loc.X, Loc.Y, Feet + Z), Dir, Wall))
		{
			bWall = true;
			break;
		}
	}
	if (!bWall)
	{
		return false;
	}
	Out.WallPoint = Wall.ImpactPoint;
	Out.WallNormal = Horizontal(Wall.ImpactNormal);
	const AActor* WallActor = Wall.GetActor();
	const UPrimitiveComponent* WallComp = Wall.GetComponent();
	Out.bClimbable = (WallActor && WallActor->ActorHasTag(ClimbableTag)) || (WallComp && WallComp->ComponentHasTag(ClimbableTag));

	// Look down onto the top, a little past the wall face.
	const FVector Probe = Wall.ImpactPoint - Out.WallNormal * 25.f;
	const FVector Start(Probe.X, Probe.Y, Feet + MaxHangReach + 30.f);
	const FVector End(Probe.X, Probe.Y, Feet + MinMantleHeight - 10.f);
	FHitResult TopHit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(TraversalTop), false, Character);
	if (GetWorld()->SweepSingleByChannel(TopHit, Start, End, FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(10.f), Params)
		&& !TopHit.bStartPenetrating && TopHit.ImpactNormal.Z > 0.7f)
	{
		Out.Top = TopHit.ImpactPoint;
		Out.Height = TopHit.ImpactPoint.Z - Feet;
		const FVector Stand = Out.Top - Out.WallNormal * (Character->GetCapsuleComponent()->GetScaledCapsuleRadius() + 5.f) + FVector(0.f, 0.f, HalfHeight + 2.f);
		Out.bHasTop = CapsuleFits(Stand);
	}
	return true;
}

void ULSTraversalComponent::SetFlying()
{
	UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	Move->StopMovementImmediately();
	Move->SetMovementMode(MOVE_Flying);
}

void ULSTraversalComponent::EndTraversal(EMovementMode Mode)
{
	State = ETraversalState::None;
	UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	Move->StopMovementImmediately();
	Move->SetMovementMode(Mode);
}

void ULSTraversalComponent::StartMantle(const FLSLedge& Ledge)
{
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
	const FVector Loc = Character->GetActorLocation();
	MantleStart = Loc;
	MantleMid = FVector(Loc.X, Loc.Y, Ledge.Top.Z + HalfHeight + 5.f);
	MantleEnd = Ledge.Top - Ledge.WallNormal * (Capsule->GetScaledCapsuleRadius() + 5.f) + FVector(0.f, 0.f, HalfHeight + 2.f);
	MantleTime = 0.f;
	MantleLength = MantleDuration * FMath::GetMappedRangeValueClamped(FVector2D(MinMantleHeight, MaxHangReach), FVector2D(0.7f, 1.2f), Ledge.Height);
	WallNormal = Ledge.WallNormal;
	State = ETraversalState::Mantling;
	SetFlying();
	Character->SetActorRotation(FRotator(0.f, (-WallNormal).Rotation().Yaw, 0.f));
}

void ULSTraversalComponent::StartHang(const FLSLedge& Ledge)
{
	const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
	WallNormal = Ledge.WallNormal;
	const FVector Hang = Ledge.WallPoint + WallNormal * (Capsule->GetScaledCapsuleRadius() + 2.f);
	const float Z = Ledge.Top.Z - HangHeight + Capsule->GetScaledCapsuleHalfHeight();
	State = ETraversalState::Hanging;
	SetFlying();
	Character->SetActorLocationAndRotation(FVector(Hang.X, Hang.Y, Z), FRotator(0.f, (-WallNormal).Rotation().Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
}

void ULSTraversalComponent::StartClimb(const FHitResult& Wall)
{
	WallNormal = Horizontal(Wall.ImpactNormal);
	State = ETraversalState::Climbing;
	bAutoRegrab = false;
	SetFlying();
	const FVector Loc = Character->GetActorLocation();
	const FVector OnWall = Wall.ImpactPoint + WallNormal * (Character->GetCapsuleComponent()->GetScaledCapsuleRadius() + 2.f);
	Character->SetActorLocationAndRotation(FVector(OnWall.X, OnWall.Y, Loc.Z), FRotator(0.f, (-WallNormal).Rotation().Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
}

void ULSTraversalComponent::TryEnter()
{
	UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	if (Now() < CooldownUntil || (Move->MovementMode != MOVE_Walking && Move->MovementMode != MOVE_Falling))
	{
		return;
	}
	const bool bFalling = Move->IsFalling();
	FVector Dir = MoveDir;
	if (Dir.IsNearlyZero() && (bFalling || bAutoRegrab))
	{
		Dir = Character->GetActorForwardVector();
	}
	if (Dir.IsNearlyZero())
	{
		return;
	}

	FLSLedge Ledge;
	if (!FindLedge(Dir, Ledge))
	{
		return;
	}
	// Only react when actually pushing into the wall (or falling past it).
	const bool bPushing = FVector::DotProduct(MoveDir, -Ledge.WallNormal) > 0.5f;

	switch (Classify(Ledge, bFalling, bPushing || bAutoRegrab, Move->Velocity.Z))
	{
	case ETraversalState::Mantling:
		StartMantle(Ledge);
		break;
	case ETraversalState::Hanging:
		StartHang(Ledge);
		break;
	case ETraversalState::Climbing:
	{
		FHitResult Wall;
		if (TraceWall(Character->GetActorLocation(), -Ledge.WallNormal, Wall))
		{
			StartClimb(Wall);
		}
		break;
	}
	default:
		break;
	}
}

ETraversalState ULSTraversalComponent::Classify(const FLSLedge& Ledge, bool bFalling, bool bPushing, float VerticalSpeed) const
{
	if (Ledge.bHasTop && Ledge.Height >= MinMantleHeight && Ledge.Height <= MaxMantleHeight && (bPushing || bFalling))
	{
		return ETraversalState::Mantling;
	}
	if (bFalling && Ledge.bHasTop && Ledge.Height > MaxMantleHeight && Ledge.Height <= MaxHangReach && VerticalSpeed <= 0.f)
	{
		return ETraversalState::Hanging;
	}
	if (Ledge.bClimbable && bPushing)
	{
		return ETraversalState::Climbing;
	}
	return ETraversalState::None;
}

void ULSTraversalComponent::TickMantle(float Dt)
{
	MantleTime += Dt;
	const float Alpha = FMath::Clamp(MantleTime / FMath::Max(MantleLength, 0.05f), 0.f, 1.f);
	// First 60% lifts, the rest moves onto the top.
	const FVector Pos = Alpha < 0.6f
		? FMath::Lerp(MantleStart, MantleMid, FMath::InterpEaseOut(0.f, 1.f, Alpha / 0.6f, 2.f))
		: FMath::Lerp(MantleMid, MantleEnd, (Alpha - 0.6f) / 0.4f);
	Character->SetActorLocation(Pos, false, nullptr, ETeleportType::TeleportPhysics);
	if (Alpha >= 1.f)
	{
		EndTraversal(MOVE_Walking);
	}
}

void ULSTraversalComponent::TickHang(float Dt)
{
	if (FMath::Abs(StickRight) < 0.2f)
	{
		return;
	}
	// Shimmy along the wall, only while a ledge continues there.
	const FVector Tangent = FVector::CrossProduct(FVector::UpVector, WallNormal) * -1.f;
	const FVector Step = Tangent * FMath::Sign(StickRight) * ShimmySpeed * Dt;
	const FVector Old = Character->GetActorLocation();
	Character->SetActorLocation(Old + Step, true);
	FLSLedge Ledge;
	if (!FindLedge(-WallNormal, Ledge) || !Ledge.bHasTop || Ledge.Height > MaxHangReach + 5.f)
	{
		Character->SetActorLocation(Old);
	}
}

void ULSTraversalComponent::TickClimb(float Dt)
{
	const FVector Loc = Character->GetActorLocation();
	const float HalfHeight = Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();

	// Reached the top: no wall at head height but a ledge to stand on.
	FHitResult HeadWall;
	if (!TraceWall(Loc + FVector(0.f, 0.f, HalfHeight * 0.8f), -WallNormal, HeadWall))
	{
		FLSLedge Ledge;
		if (FindLedge(-WallNormal, Ledge) && Ledge.bHasTop)
		{
			StartMantle(Ledge);
		}
		else
		{
			Drop();
		}
		return;
	}

	FHitResult Wall;
	if (!TraceWall(Loc, -WallNormal, Wall))
	{
		Drop();
		return;
	}
	WallNormal = Horizontal(Wall.ImpactNormal);

	const FVector Tangent = FVector::CrossProduct(FVector::UpVector, WallNormal) * -1.f;
	const FVector Delta = (FVector::UpVector * StickForward + Tangent * StickRight).GetClampedToMaxSize(1.f) * ClimbSpeed * Dt;
	FVector Target = Wall.ImpactPoint + WallNormal * (Character->GetCapsuleComponent()->GetScaledCapsuleRadius() + 2.f);
	Target.Z = Loc.Z;
	Target += Delta;

	FHitResult Blocked;
	Character->SetActorLocationAndRotation(Target, FRotator(0.f, (-WallNormal).Rotation().Yaw, 0.f), true, &Blocked);

	// Climbing down onto the ground ends the climb.
	if (StickForward < -0.2f && Blocked.bBlockingHit && Blocked.ImpactNormal.Z > 0.7f)
	{
		EndTraversal(MOVE_Walking);
	}
}

bool ULSTraversalComponent::Jump()
{
	switch (State)
	{
	case ETraversalState::Hanging:
	{
		FLSLedge Ledge;
		if (FindLedge(-WallNormal, Ledge) && Ledge.bHasTop)
		{
			StartMantle(Ledge);
		}
		return true;
	}
	case ETraversalState::Climbing:
	{
		const float Gravity = FMath::Abs(Character->GetCharacterMovement()->GetGravityZ());
		const FVector Tangent = FVector::CrossProduct(FVector::UpVector, WallNormal) * -1.f;
		FVector Launch;
		if (FMath::Abs(StickRight) < 0.2f && StickForward < -0.2f)
		{
			// Back away from the wall.
			Launch = WallNormal * 450.f + FVector(0.f, 0.f, 300.f);
			CooldownUntil = Now() + RegrabCooldown;
		}
		else
		{
			// Hop ClimbHopDistance up or sideways and re-grab.
			const float Up = FMath::Sqrt(2.f * Gravity * ClimbHopDistance);
			Launch = FMath::Abs(StickRight) >= 0.2f
				? Tangent * FMath::Sign(StickRight) * 350.f + FVector(0.f, 0.f, Up * 0.6f) - WallNormal * 50.f
				: FVector(0.f, 0.f, Up) - WallNormal * 50.f;
			bAutoRegrab = true;
			CooldownUntil = Now() + 0.15;
		}
		State = ETraversalState::None;
		Character->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
		Character->LaunchCharacter(Launch, true, true);
		return true;
	}
	case ETraversalState::Mantling:
		return true;
	default:
		return false;
	}
}

void ULSTraversalComponent::Drop()
{
	if (State == ETraversalState::Hanging || State == ETraversalState::Climbing)
	{
		CooldownUntil = Now() + RegrabCooldown;
		bAutoRegrab = false;
		EndTraversal(MOVE_Falling);
	}
}

void ULSTraversalComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	if (!Character)
	{
		return;
	}
	switch (State)
	{
	case ETraversalState::None:
		TryEnter();
		if (bAutoRegrab && Character->GetCharacterMovement()->IsMovingOnGround())
		{
			bAutoRegrab = false;
		}
		break;
	case ETraversalState::Mantling:
		TickMantle(DeltaTime);
		break;
	case ETraversalState::Hanging:
		TickHang(DeltaTime);
		break;
	case ETraversalState::Climbing:
		TickClimb(DeltaTime);
		break;
	}
}

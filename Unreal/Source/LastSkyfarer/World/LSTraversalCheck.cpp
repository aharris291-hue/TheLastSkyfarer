// The Last Skyfarer: end-to-end traversal check run in a real game world (-LSTraversalCheck).

#include "LSTraversalCheck.h"

#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "LSPlayerCharacter.h"
#include "LSTraversalComponent.h"
#include "LSStorySubsystem.h"

namespace
{
	// Block faces are at X = 0; Kieran starts 1.5 m in front of them facing +X.
	const FVector MantleLane(0.f, -2000.f, 0.f);
	const FVector HangLane(0.f, -1000.f, 0.f);
	const FVector ClimbLane(0.f, 2000.f, 0.f);
	constexpr float MantleHeight = 120.f;
	constexpr float HangTop = 320.f; // out of mantle reach from the ground; reachable by jumping
	constexpr float ClimbTop = 600.f;
}

ALSTraversalCheck::ALSTraversalCheck()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
}

ALSPlayerCharacter* ALSTraversalCheck::Kieran() const
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	return PC ? Cast<ALSPlayerCharacter>(PC->GetPawn()) : nullptr;
}

float ALSTraversalCheck::Feet() const
{
	const ALSPlayerCharacter* K = Kieran();
	return K ? K->GetActorLocation().Z - K->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() : 0.f;
}

void ALSTraversalCheck::SpawnBlock(const FVector& Center, const FVector& Size, bool bClimbable)
{
	AStaticMeshActor* A = GetWorld()->SpawnActor<AStaticMeshActor>(Center, FRotator::ZeroRotator);
	UStaticMeshComponent* C = A->GetStaticMeshComponent();
	C->SetMobility(EComponentMobility::Movable);
	C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
	C->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	A->SetActorScale3D(Size / 100.f);
	if (bClimbable)
	{
		A->Tags.Add(TEXT("Climbable"));
	}
}

void ALSTraversalCheck::BeginPlay()
{
	Super::BeginPlay();
	SpawnBlock(MantleLane + FVector(100.f, 0.f, MantleHeight / 2.f), FVector(200.f, 400.f, MantleHeight), false);
	SpawnBlock(HangLane + FVector(100.f, 0.f, HangTop / 2.f), FVector(200.f, 400.f, HangTop), false);
	SpawnBlock(ClimbLane + FVector(100.f, 0.f, ClimbTop / 2.f), FVector(200.f, 400.f, ClimbTop), true);
}

void ALSTraversalCheck::Place(const FVector& FeetLocation)
{
	ALSPlayerCharacter* K = Kieran();
	K->GetCharacterMovement()->StopMovementImmediately();
	K->SetActorLocationAndRotation(FeetLocation + FVector(0.f, 0.f, K->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.f),
		FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
	K->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
}

void ALSTraversalCheck::Push(const FVector& Dir, float StickRight, float StickForward)
{
	ALSPlayerCharacter* K = Kieran();
	K->Traversal->SetMoveInput(Dir, StickRight, StickForward);
	if (!Dir.IsNearlyZero() && !K->Traversal->IsBusy())
	{
		K->AddMovementInput(Dir);
	}
}

void ALSTraversalCheck::Report(const TCHAR* Case, bool bPass, const FString& Detail)
{
	++Total;
	Passed += bPass ? 1 : 0;
	UE_LOG(LogTemp, Display, TEXT("LS_TRAV %s %s (%s)"), Case, bPass ? TEXT("PASS") : TEXT("FAIL"), *Detail);
}

void ALSTraversalCheck::NextStep()
{
	++Step;
	StepTime = 0.f;
}

void ALSTraversalCheck::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ALSPlayerCharacter* K = Kieran();
	if (!K)
	{
		return;
	}
	StepTime += DeltaSeconds;
	const ETraversalState State = K->Traversal->GetState();

	switch (Step)
	{
	case 0: // settle, and click through any story dialogue (it blocks movement)
		if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
		{
			if (Story->IsInDialogue())
			{
				Story->AdvanceDialogue();
				StepTime = 0.f;
				break;
			}
		}
		if (StepTime > 1.f) { Place(MantleLane + FVector(-150.f, 0.f, 0.f)); NextStep(); }
		break;
	case 1: // walk into a 1.2 m block, then stop on top
		Push(Feet() < MantleHeight - 20.f || State != ETraversalState::None ? FVector::ForwardVector : FVector::ZeroVector, 0.f, 1.f);
		if (StepTime > 3.f)
		{
			Report(TEXT("Mantle1.2m"), FMath::IsNearlyEqual(Feet(), MantleHeight, 15.f) && State == ETraversalState::None,
				FString::Printf(TEXT("feet %.0f cm, expected %.0f"), Feet(), MantleHeight));
			Place(HangLane + FVector(-(K->GetCapsuleComponent()->GetScaledCapsuleRadius() + 8.f), 0.f, 0.f));
			NextStep();
		}
		break;
	case 2: // jump at a 3.2 m ledge and catch it
		Push(bHangSeen ? FVector::ZeroVector : FVector::ForwardVector, 0.f, 0.f);
		if (!bHangSeen && StepTime > 0.4f && StepTime - DeltaSeconds <= 0.4f)
		{
			K->DoJumpStart();
		}
		if (State == ETraversalState::Hanging && !bHangSeen)
		{
			bHangSeen = true;
			Report(TEXT("LedgeGrab"), FMath::IsNearlyEqual(HangTop - Feet(), K->Traversal->HangHeight, 10.f),
				FString::Printf(TEXT("ledge %.0f cm above feet, expected %.0f"), HangTop - Feet(), K->Traversal->HangHeight));
			StepTime = 0.f;
		}
		if (bHangSeen && StepTime > 0.5f)
		{
			K->Traversal->Jump();
			NextStep();
		}
		else if (!bHangSeen && StepTime > 3.f)
		{
			Report(TEXT("LedgeGrab"), false, FString::Printf(TEXT("never grabbed; feet %.0f cm"), Feet()));
			Report(TEXT("PullUp"), false, TEXT("skipped"));
			Place(ClimbLane + FVector(-150.f, 0.f, 0.f));
			Step = 4;
			StepTime = 0.f;
		}
		break;
	case 3: // pull up
		Push(FVector::ZeroVector, 0.f, 0.f);
		if (StepTime > 1.5f)
		{
			Report(TEXT("PullUp"), FMath::IsNearlyEqual(Feet(), HangTop, 15.f) && State == ETraversalState::None,
				FString::Printf(TEXT("feet %.0f cm, expected %.0f"), Feet(), HangTop));
			Place(ClimbLane + FVector(-150.f, 0.f, 0.f));
			NextStep();
		}
		break;
	case 4: // climb a 6 m tagged wall
		Push(FVector::ForwardVector, 0.f, 1.f);
		if (State == ETraversalState::None && FMath::IsNearlyEqual(Feet(), ClimbTop, 15.f) && StepTime > 1.f)
		{
			Report(TEXT("Climb6m"), true, FString::Printf(TEXT("reached the top in %.1f s"), StepTime));
			NextStep();
		}
		else if (StepTime > 10.f)
		{
			Report(TEXT("Climb6m"), false, FString::Printf(TEXT("feet %.0f cm after 10 s, state %d"), Feet(), static_cast<int32>(State)));
			NextStep();
		}
		break;
	case 5:
		UE_LOG(LogTemp, Display, TEXT("LS_TRAV_SUMMARY %d/%d passed"), Passed, Total);
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			PC->ConsoleCommand(TEXT("quit"));
		}
		NextStep();
		break;
	default:
		break;
	}
}

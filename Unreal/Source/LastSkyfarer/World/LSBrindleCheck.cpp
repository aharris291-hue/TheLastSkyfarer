// The Last Skyfarer: scripted check of the Brindle Isle greybox (-LSBrindleCheck).

#include "LSBrindleCheck.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GliderComponent.h"
#include "HAL/FileManager.h"
#include "LSCompassComponent.h"
#include "LSHUD.h"
#include "LSInteractorComponent.h"
#include "LSMapWidget.h"
#include "LSPlayerCharacter.h"
#include "LSStorySubsystem.h"
#include "LSTraversalComponent.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

namespace
{
	constexpr float M = 100.f;
}

ALSBrindleCheck::ALSBrindleCheck()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

void ALSBrindleCheck::Check(const TCHAR* Name, bool bPass, const FString& Detail)
{
	++Total;
	Passed += bPass ? 1 : 0;
	UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE %s %s (%s)"), Name, bPass ? TEXT("PASS") : TEXT("FAIL"), *Detail);
}

void ALSBrindleCheck::Shot(const TCHAR* Name)
{
	const FString Dir = FPaths::ProjectSavedDir() / TEXT("Screenshots");
	IFileManager::Get().MakeDirectory(*Dir, true);
	FScreenshotRequest::RequestScreenshot(Dir / FString::Printf(TEXT("L_Brindle_%s.png"), Name), true, false);
	UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE screenshot %s"), Name);
}

void ALSBrindleCheck::Next()
{
	++Step;
	StepTime = 0.f;
	AdvanceTimer = 0.f;
	bShot = false;
}

void ALSBrindleCheck::HandlePulse(const FLSCompassReading& Reading)
{
	++Pulses;
}

bool ALSBrindleCheck::PumpDialogue(float Dt)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story->IsInDialogue())
	{
		return true;
	}
	AdvanceTimer += Dt;
	if (AdvanceTimer >= 0.5f)
	{
		AdvanceTimer = 0.f;
		Story->AdvanceDialogue();
	}
	return false;
}

void ALSBrindleCheck::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	ALSPlayerCharacter* K = PC ? Cast<ALSPlayerCharacter>(PC->GetPawn()) : nullptr;
	ALSHUD* H = PC ? Cast<ALSHUD>(PC->GetHUD()) : nullptr;
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!K || !H || !Story)
	{
		return;
	}
	const bool bFirst = StepTime == 0.f; // first tick of this step
	StepTime += DeltaSeconds;
	auto Feet = [K]() { return K->GetActorLocation(); };

	switch (Step)
	{
	case 0: // overview from high above the south-west, looking at the island
		if (bFirst)
		{
			OverviewCamera = GetWorld()->SpawnActor<ACameraActor>(FVector(-900.f * M, -700.f * M, 420.f * M), FRotator(-24.f, 38.f, 0.f));
			OverviewCamera->GetCameraComponent()->SetFieldOfView(70.f);
			PC->SetViewTarget(OverviewCamera);
		}
		if (StepTime > 3.f && !bShot)
		{
			Shot(TEXT("overview"));
			bShot = true;
		}
		if (StepTime > 3.6f)
		{
			PC->SetViewTarget(K);
			Next();
		}
		break;
	case 1: // the opening on the Upper Cliffs (D-15)
		if (StepTime > 0.5f && !bShot)
		{
			Check(TEXT("StartsOnUpperCliffs"), Story->GetState().Discovered.Contains(TEXT("upper_cliffs")) || Feet().Z > 14.f * M,
				FString::Printf(TEXT("Kieran at %s"), *(Feet() / M).ToCompactString()));
			Check(TEXT("OpeningPlays"), Story->IsInDialogue() || Story->HasFlag(TEXT("opening_seen")), TEXT("opening conversation"));
			bShot = true;
		}
		if (StepTime > 0.5f && PumpDialogue(DeltaSeconds))
		{
			Check(TEXT("MorningDeliveriesStarted"), Story->GetQuestState(TEXT("morning_deliveries")) == ELSQuestState::Active, TEXT("quest active"));
			Next();
		}
		break;
	case 2: // walk into the village square from the north-east road
		if (bFirst)
		{
			K->SetActorLocationAndRotation(FVector(40.f * M, 45.f * M, 1.2f * M), FRotator(0.f, -130.f, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
			PC->SetControlRotation(FRotator(-10.f, -130.f, 0.f));
		}
		if (StepTime < 2.5f)
		{
			K->AddMovementInput(FRotator(0.f, -130.f, 0.f).Vector());
		}
		if (StepTime > 3.f && !bShot)
		{
			Check(TEXT("WalksIntoVillage"), Story->GetState().Discovered.Contains(TEXT("windrest")),
				FString::Printf(TEXT("at %s"), *(Feet() / M).ToCompactString()));
			Shot(TEXT("square"));
			bShot = true;
		}
		if (StepTime > 3.6f)
		{
			Next();
		}
		break;
	case 3: // the map screen, with a pin
		if (bFirst)
		{
			H->ToggleMap();
		}
		if (StepTime > 1.5f && !bShot)
		{
			H->GetMapWidget()->ClickAt(FVector2D(0.62f, 0.3f));
			Check(TEXT("MapOpens"), H->IsMapOpen() && H->GetMapWidget()->GetDrawnMarkerCount() > 0,
				FString::Printf(TEXT("%d markers drawn"), H->GetMapWidget()->GetDrawnMarkerCount()));
			Check(TEXT("MapPin"), Story->GetMapPins().Num() == 1, FString::Printf(TEXT("%d pins"), Story->GetMapPins().Num()));
			bShot = true;
		}
		if (StepTime > 2.f && StepTime - DeltaSeconds <= 2.f)
		{
			Shot(TEXT("map"));
		}
		if (StepTime > 2.6f)
		{
			H->ToggleMap();
			Next();
		}
		break;
	case 4: // compass pulse (unlocked here for the check; in the story it wakes in Chapter 2)
		if (bFirst)
		{
			K->Compass->OnPulse.AddUniqueDynamic(this, &ALSBrindleCheck::HandlePulse);
			Story->SetFlag(TEXT("compass_active"));
			K->Compass->Pulse();
		}
		if (StepTime > 0.8f && !bShot)
		{
			Check(TEXT("CompassPulse"), Pulses == 1, FString::Printf(TEXT("%d pulse"), Pulses));
			Shot(TEXT("compass"));
			bShot = true;
		}
		if (StepTime > 1.4f)
		{
			Next();
		}
		break;
	case 5: // glide off Old Cartographer's Bluff, eastwards
		if (bFirst)
		{
			K->SetActorLocationAndRotation(FVector(60.f * M, 670.f * M, 22.f * M), FRotator(0.f, 90.f, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
			PC->SetControlRotation(FRotator(-8.f, 90.f, 0.f));
			GlideStart = Feet();
		}
		if (StepTime < 6.f && !K->Glider->IsGliding())
		{
			K->Traversal->SetMoveInput(FVector(0.f, 1.f, 0.f), 0.f, 1.f);
			K->AddMovementInput(FVector(0.f, 1.f, 0.f));
			if (K->GetCharacterMovement()->IsFalling() && K->GetActorLocation().Z < GlideStart.Z - 2.f * M)
			{
				K->DoJumpStart(); // deploy the glider once clear of the edge
			}
		}
		if (StepTime > 9.f && !bShot)
		{
			const FVector P = Feet();
			Check(TEXT("GlideOffBluff"), K->Glider->IsGliding() && P.Y > GlideStart.Y + 40.f * M,
				FString::Printf(TEXT("gliding=%d, %.0f m east of the edge, %.0f m below it, airspeed %.1f m/s"), K->Glider->IsGliding() ? 1 : 0,
					(P.Y - GlideStart.Y) / M, (GlideStart.Z - P.Z) / M, K->Glider->GetAirspeed()));
			Shot(TEXT("glide"));
			bShot = true;
		}
		if (StepTime > 9.6f)
		{
			Next();
		}
		break;
	case 6:
		UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE_SUMMARY %d/%d passed"), Passed, Total);
		PC->ConsoleCommand(TEXT("quit"));
		Next();
		break;
	default:
		break;
	}
}

// The Last Skyfarer: scripted UI and story playthrough of L_SystemsTest (-LSPlaythrough).

#include "LSPlaythroughCheck.h"

#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "LSHUD.h"
#include "LSHUDWidget.h"
#include "LSInteractorComponent.h"
#include "LSJournalWidget.h"
#include "LSPauseWidget.h"
#include "LSPlayerCharacter.h"
#include "LSStorySubsystem.h"
#include "LSStoryVolumes.h"
#include "LSTimeOfDayDirector.h"
#include "Engine/DirectionalLight.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

ALSPlaythroughCheck::ALSPlaythroughCheck()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

ALSPlayerCharacter* ALSPlaythroughCheck::Kieran() const
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	return PC ? Cast<ALSPlayerCharacter>(PC->GetPawn()) : nullptr;
}

ALSHUD* ALSPlaythroughCheck::HUD() const
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	return PC ? Cast<ALSHUD>(PC->GetHUD()) : nullptr;
}

void ALSPlaythroughCheck::Check(const TCHAR* Name, bool bPass, const FString& Detail)
{
	++Total;
	Passed += bPass ? 1 : 0;
	UE_LOG(LogTemp, Display, TEXT("LS_PLAY %s %s (%s)"), Name, bPass ? TEXT("PASS") : TEXT("FAIL"), *Detail);
}

void ALSPlaythroughCheck::Shot(const TCHAR* Name)
{
	const FString Dir = FPaths::ProjectSavedDir() / TEXT("Screenshots");
	IFileManager::Get().MakeDirectory(*Dir, true);
	FScreenshotRequest::RequestScreenshot(Dir / FString::Printf(TEXT("L_SystemsTest_%s.png"), Name), /*bShowUI*/ true, false);
	UE_LOG(LogTemp, Display, TEXT("LS_PLAY screenshot %s"), Name);
}

void ALSPlaythroughCheck::Next()
{
	++Step;
	StepTime = 0.f;
	AdvanceTimer = 0.f;
	bShotTaken = false;
}

void ALSPlaythroughCheck::HandleNotify(const FText& Message)
{
	++Toasts;
	LastToast = Message.ToString();
}

bool ALSPlaythroughCheck::PumpDialogue(float Dt)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story->IsInDialogue())
	{
		return true;
	}
	AdvanceTimer += Dt;
	if (AdvanceTimer >= 0.6f)
	{
		AdvanceTimer = 0.f;
		Kieran()->Interactor->Interact(); // E advances dialogue
	}
	return false;
}

void ALSPlaythroughCheck::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ALSPlayerCharacter* K = Kieran();
	ALSHUD* H = HUD();
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!K || !H || !Story || !H->GetHUDWidget())
	{
		return;
	}
	StepTime += DeltaSeconds;

	switch (Step)
	{
	case 0: // the opening plays when Kieran spawns inside its trigger
		Story->OnNotify.AddUniqueDynamic(this, &ALSPlaythroughCheck::HandleNotify);
		if (H->GetHUDWidget()->IsDialogueOpen())
		{
			Check(TEXT("OpeningDialogueShown"), true, FString::Printf(TEXT("[%s] %s"),
				*H->GetHUDWidget()->GetDialogueSpeaker().ToString(), *H->GetHUDWidget()->GetDialogueText().ToString()));
			Next();
		}
		else if (StepTime > 5.f)
		{
			Check(TEXT("OpeningDialogueShown"), false, TEXT("no dialogue within 5 s"));
			Next();
		}
		break;
	case 1: // screenshot on the canon line, then play the opening through
		if (!bShotTaken && H->GetHUDWidget()->GetDialogueText().ToString().Contains(TEXT("more out there")))
		{
			Shot(TEXT("dialogue"));
			bShotTaken = true;
			AdvanceTimer = -1.f; // hold the line on screen for the screenshot
		}
		if (PumpDialogue(DeltaSeconds))
		{
			Check(TEXT("QuestStartedByOpening"), Story->GetQuestState(TEXT("morning_deliveries")) == ELSQuestState::Active,
				FString::Printf(TEXT("tracked quest %s"), *Story->GetTrackedQuest().ToString()));
			Check(TEXT("QuestToast"), Toasts > 0, FString::Printf(TEXT("%d toasts, last: %s"), Toasts, *LastToast));
			Next();
		}
		break;
	case 2: // walk up to the test NPC and talk
	{
		ALSStoryNPC* Maren = nullptr;
		for (TActorIterator<ALSStoryNPC> It(GetWorld()); It; ++It) { Maren = *It; }
		if (!Maren)
		{
			Check(TEXT("TalkToNPC"), false, TEXT("no NPC in the level"));
			Step = 4;
			break;
		}
		if (StepTime < DeltaSeconds * 1.5f)
		{
			const FVector To = Maren->GetActorLocation() + Maren->GetActorForwardVector() * 150.f;
			K->SetActorLocation(FVector(To.X, To.Y, K->GetActorLocation().Z), false, nullptr, ETeleportType::TeleportPhysics);
		}
		if (StepTime > 0.5f)
		{
			const FText Prompt = K->Interactor->GetPrompt();
			Check(TEXT("InteractionPrompt"), !Prompt.IsEmpty(), FString::Printf(TEXT("prompt '%s'"), *Prompt.ToString()));
			K->Interactor->Interact();
			Check(TEXT("TalkToNPC"), Story->IsInDialogue(), TEXT("Maren's conversation started"));
			Next();
		}
		break;
	}
	case 3:
		if (PumpDialogue(DeltaSeconds))
		{
			Check(TEXT("ObjectiveAdvanced"), Story->IsObjectiveDone(TEXT("morning_deliveries"), TEXT("report")),
				TEXT("morning_deliveries:report done after Maren's briefing"));
			Next();
		}
		break;
	case 4: // pick up Elias's note
	{
		ALSJournalPickup* Note = nullptr;
		for (TActorIterator<ALSJournalPickup> It(GetWorld()); It; ++It) { Note = *It; }
		if (Note && StepTime < DeltaSeconds * 1.5f)
		{
			K->SetActorLocation(Note->GetActorLocation() + FVector(-120.f, 0.f, 60.f), false, nullptr, ETeleportType::TeleportPhysics);
		}
		if (StepTime > 0.5f && StepTime - DeltaSeconds <= 0.5f)
		{
			K->Interactor->Interact();
		}
		if (StepTime > 1.f && PumpDialogue(DeltaSeconds))
		{
			Check(TEXT("JournalPickup"), Story->HasJournal(TEXT("note_wind")), TEXT("note_wind in the journal"));
			Next();
		}
		break;
	}
	case 5: // journal: Elias tab, screenshot, Quests tab
		if (StepTime < DeltaSeconds * 1.5f)
		{
			H->ToggleJournal();
			H->GetJournalWidget()->ShowTab(ELSJournalTab::Elias);
		}
		if (StepTime > 0.5f && !bShotTaken)
		{
			Check(TEXT("JournalOpens"), H->IsJournalOpen() && H->GetJournalWidget()->GetEntryCount() >= 1,
				FString::Printf(TEXT("Elias tab lists %d entries"), H->GetJournalWidget()->GetEntryCount()));
			Shot(TEXT("journal"));
			bShotTaken = true;
		}
		if (StepTime > 1.5f)
		{
			H->GetJournalWidget()->ShowTab(ELSJournalTab::Quests);
			Check(TEXT("JournalQuestsTab"), H->GetJournalWidget()->GetEntryCount() >= 2, FString::Printf(TEXT("%d quests listed"), H->GetJournalWidget()->GetEntryCount()));
			H->ToggleJournal();
			Next();
		}
		break;
	case 6: // pause menu: save
		if (StepTime < DeltaSeconds * 1.5f)
		{
			H->TogglePause();
			H->GetPauseWidget()->SlotName = TEXT("playthrough_check");
			H->GetPauseWidget()->Save();
		}
		if (StepTime > 0.5f)
		{
			Check(TEXT("PauseAndSave"), H->IsPauseOpen() && ULSStorySubsystem::DoesSlotExist(TEXT("playthrough_check")), TEXT("saved from the pause menu"));
			H->TogglePause();
			Next();
		}
		break;
	case 7: // time of day: Sunset, then Night
	case 8:
	{
		const FName Wanted = Step == 7 ? FName(TEXT("Sunset")) : FName(TEXT("Night"));
		if (StepTime < DeltaSeconds * 1.5f)
		{
			Story->SetTimeOfDay(Wanted);
		}
		if (StepTime > 4.f)
		{
			ALSTimeOfDayDirector* Director = nullptr;
			for (TActorIterator<ALSTimeOfDayDirector> It(GetWorld()); It; ++It) { Director = *It; }
			ADirectionalLight* Sun = nullptr;
			for (TActorIterator<ADirectionalLight> It(GetWorld()); It; ++It) { Sun = *It; }
			const FLSTimeOfDayPreset* Preset = Director ? Director->Presets.Find(Wanted) : nullptr;
			const bool bOk = Director && Sun && Preset && Director->GetCurrent() == Wanted
				&& FMath::IsNearlyEqual(Sun->GetActorRotation().Pitch, Preset->SunRotation.Pitch, 1.f);
			Check(Step == 7 ? TEXT("TimeOfDaySunset") : TEXT("TimeOfDayNight"), bOk,
				FString::Printf(TEXT("sun pitch %.1f"), Sun ? Sun->GetActorRotation().Pitch : 0.f));
			Shot(Step == 7 ? TEXT("sunset") : TEXT("night"));
			Next();
		}
		break;
	}
	case 9:
		if (StepTime < 0.5f)
		{
			break; // let the last screenshot finish
		}
		UE_LOG(LogTemp, Display, TEXT("LS_PLAY_SUMMARY %d/%d passed"), Passed, Total);
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			PC->ConsoleCommand(TEXT("quit"));
		}
		Next();
		break;
	default:
		break;
	}
}

// The Last Skyfarer: scripted Milestone A run on Brindle Isle (-LSBrindleCheck).

#include "LSBrindleCheck.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GliderComponent.h"
#include "HAL/FileManager.h"
#include "LSBrindleStory.h"
#include "LSCompassComponent.h"
#include "LSHUD.h"
#include "LSInteractableComponent.h"
#include "LSMapWidget.h"
#include "LSPlayerCharacter.h"
#include "LSStorySubsystem.h"
#include "LSStoryVolumes.h"
#include "LSTraversalComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "PikoCompanion.h"
#include "UnrealClient.h"

namespace
{
	constexpr float CmPerM = 100.f;
	const TCHAR* SaveSlot = TEXT("milestone_a_bot");
}

ALSBrindleCheck::ALSBrindleCheck()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

void ALSBrindleCheck::BeginPlay()
{
	Super::BeginPlay();
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnDialogueLine.AddUniqueDynamic(this, &ALSBrindleCheck::HandleLine);
	}
	Build();
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

void ALSBrindleCheck::ShotFrom(const FVector& Where, const FRotator& Rot)
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!ShotCamera)
	{
		ShotCamera = GetWorld()->SpawnActor<ACameraActor>(Where, Rot);
		ShotCamera->GetCameraComponent()->SetFieldOfView(70.f);
	}
	ShotCamera->SetActorLocationAndRotation(Where, Rot);
	PC->SetViewTarget(ShotCamera);
}

void ALSBrindleCheck::Place(const FVector& WhereM, float Yaw)
{
	ALSPlayerCharacter* K = Kieran();
	K->GetCharacterMovement()->StopMovementImmediately();
	K->SetActorLocationAndRotation(WhereM * CmPerM, FRotator(0.f, Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	GetWorld()->GetFirstPlayerController()->SetControlRotation(FRotator(-10.f, Yaw, 0.f));
}

bool ALSBrindleCheck::Talk(ULSInteractableComponent* Target, const TCHAR* What)
{
	if (!Target)
	{
		Check(What, false, TEXT("not found in the level"));
		return true;
	}
	if (!Target->Interact(Kieran()))
	{
		Check(What, false, TEXT("interaction refused"));
	}
	return true;
}

bool ALSBrindleCheck::At(float Seconds) const
{
	return LastStepTime < Seconds && CurStepTime >= Seconds;
}

bool ALSBrindleCheck::IsIdle() const
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	const ALSBrindleStory* D = Director();
	return !Story->IsInDialogue() && (!D || !D->IsBusy());
}

ALSPlayerCharacter* ALSBrindleCheck::Kieran() const
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	return PC ? Cast<ALSPlayerCharacter>(PC->GetPawn()) : nullptr;
}

ALSBrindleStory* ALSBrindleCheck::Director() const
{
	for (TActorIterator<ALSBrindleStory> It(GetWorld()); It; ++It)
	{
		return *It;
	}
	return nullptr;
}

ULSInteractableComponent* ALSBrindleCheck::FindByPrompt(const FString& Prompt) const
{
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (ULSInteractableComponent* I = It->FindComponentByClass<ULSInteractableComponent>(); I && I->Prompt.ToString() == Prompt)
		{
			return I;
		}
	}
	return nullptr;
}

ULSInteractableComponent* ALSBrindleCheck::FindSpeaker(FName Speaker) const
{
	for (TActorIterator<ALSStoryNPC> It(GetWorld()); It; ++It)
	{
		if (It->SpeakerId == Speaker)
		{
			return It->Interactable;
		}
	}
	return nullptr;
}

void ALSBrindleCheck::HandlePulse(const FLSCompassReading& Reading)
{
	++Pulses;
}

void ALSBrindleCheck::HandleLine(FName ConversationId, const FLSDialogueLine& Line)
{
	if (Conversations.Num() == 0 || Conversations.Last() != ConversationId)
	{
		Conversations.Add(ConversationId);
		UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE conversation %s"), *ConversationId.ToString());
	}
}

void ALSBrindleCheck::Add(const FString& Name, TFunction<bool(float)> Run)
{
	Actions.Add({ Name, MoveTemp(Run) });
}

void ALSBrindleCheck::Build()
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	auto Quest = [Story](const TCHAR* Q) { return Story->GetQuestState(Q); };
	auto Done = [Story](const TCHAR* Q, const TCHAR* O) { return Story->IsObjectiveDone(Q, O); };
	auto Tod = [Story]() { return Story->GetTimeOfDay().ToString(); };

	if (FParse::Param(FCommandLine::Get(), TEXT("LSContinueCheck")))
	{
		// Opened by the title screen's Continue: the save is loaded and Kieran is back where it was made.
		Add(TEXT("continue"), [this, Story, Tod](float T)
		{
			if (!At(0.3f))
			{
				return false;
			}
			const FTransform& Saved = Story->GetState().PlayerTransform;
			const float Dist = FVector::Dist(Kieran()->GetActorLocation(), Saved.GetLocation());
			Check(TEXT("ContinueLoadsSave"), Story->GetChapter() > 1 && Story->HasFlag(TEXT("opening_done")) && !Conversations.Contains(TEXT("opening")),
				FString::Printf(TEXT("chapter %d, time %s, %d flags"), Story->GetChapter(), *Tod(), Story->GetState().Flags.Num()));
			Check(TEXT("ContinueRestoresPosition"), Dist < 300.f, FString::Printf(TEXT("%.1f m from the saved position %s"), Dist / CmPerM, *(Saved.GetLocation() / CmPerM).ToCompactString()));
			Shot(TEXT("continue"));
			return true;
		});
		Add(TEXT("summary"), [this](float T)
		{
			if (T < 1.f)
			{
				return false;
			}
			UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE_SUMMARY %d/%d passed"), Passed, Total);
			GetWorld()->GetFirstPlayerController()->ConsoleCommand(TEXT("quit"));
			return true;
		});
		return;
	}

	// ---- Chapter 1: The Edge of Tomorrow
	Add(TEXT("overview"), [this](float T)
	{
		if (T == 0.f)
		{
			ShotFrom(FVector(-900.f * CmPerM, -700.f * CmPerM, 420.f * CmPerM), FRotator(-24.f, 38.f, 0.f));
		}
		if (At(3.f))
		{
			Shot(TEXT("overview"));
		}
		if (T > 3.6f)
		{
			GetWorld()->GetFirstPlayerController()->SetViewTarget(Kieran());
			return true;
		}
		return false;
	});
	Add(TEXT("opening"), [this, Story, Quest](float T)
	{
		Check(TEXT("StartsOnUpperCliffs"), Story->GetState().Discovered.Contains(TEXT("upper_cliffs")), TEXT("upper_cliffs discovered at the start"));
		Check(TEXT("OpeningPlays"), Story->HasFlag(TEXT("opening_done")) && Conversations.Contains(TEXT("opening")), TEXT("opening conversation"));
		Check(TEXT("MorningDeliveriesStarted"), Quest(TEXT("morning_deliveries")) == ELSQuestState::Active, TEXT("quest active"));
		return true;
	});
	Add(TEXT("village"), [this, Story](float T)
	{
		if (T == 0.f)
		{
			Place(FVector(40.f, 45.f, 1.2f), -130.f);
		}
		if (T < 2.5f)
		{
			Kieran()->AddMovementInput(FRotator(0.f, -130.f, 0.f).Vector());
		}
		if (At(3.f))
		{
			Check(TEXT("WalksIntoVillage"), Story->GetState().Discovered.Contains(TEXT("windrest")), FString::Printf(TEXT("at %s"), *(Kieran()->GetActorLocation() / CmPerM).ToCompactString()));
			Shot(TEXT("square"));
		}
		return T > 3.6f;
	});
	Add(TEXT("rowan"), [this](float T) { return Talk(FindSpeaker(TEXT("rowan")), TEXT("TalksToRowan")); });
	Add(TEXT("rowan check"), [this, Story](float T)
	{
		Check(TEXT("TalksToRowan"), Conversations.Contains(TEXT("rowan_morning")) && Story->HasFlag(TEXT("rowan_morning_done")), TEXT("rowan_morning"));
		return true;
	});
	Add(TEXT("map"), [this, Story](float T)
	{
		ALSHUD* H = Cast<ALSHUD>(GetWorld()->GetFirstPlayerController()->GetHUD());
		if (T == 0.f)
		{
			H->ToggleMap();
		}
		if (At(1.5f))
		{
			H->GetMapWidget()->ClickAt(FVector2D(0.62f, 0.3f));
			Check(TEXT("MapOpens"), H->IsMapOpen() && H->GetMapWidget()->GetDrawnMarkerCount() > 0, FString::Printf(TEXT("%d markers drawn"), H->GetMapWidget()->GetDrawnMarkerCount()));
			Check(TEXT("MapPin"), Story->GetMapPins().Num() == 1, FString::Printf(TEXT("%d pins"), Story->GetMapPins().Num()));
		}
		if (At(2.f))
		{
			Shot(TEXT("map"));
		}
		if (T > 2.6f)
		{
			H->ToggleMap();
			return true;
		}
		return false;
	});
	Add(TEXT("maren intro"), [this](float T) { Place(FVector(51.f, 58.f, 1.2f), 135.f); return Talk(FindSpeaker(TEXT("maren")), TEXT("MarenIntro")); });
	Add(TEXT("maren intro check"), [this, Story, Done, Tod](float T)
	{
		Check(TEXT("MarenGivesParcels"), Done(TEXT("morning_deliveries"), TEXT("report")) && Story->GetItemCount(TEXT("parcel_tavern")) == 1
			&& Story->GetItemCount(TEXT("parcel_tessa")) == 1 && Story->GetItemCount(TEXT("parcel_cliffs")) == 1, TEXT("three parcels"));
		Check(TEXT("MorningLight"), Tod() == TEXT("Morning"), Tod());
		return true;
	});
	Add(TEXT("tavern"), [this](float T) { Place(FVector(-56.f, 106.f, 1.2f), 135.f); return Talk(FindSpeaker(TEXT("tavern")), TEXT("TavernDelivery")); });
	Add(TEXT("tessa"), [this](float T) { Place(FVector(472.f, 32.f, 26.8f), 45.f); return Talk(FindSpeaker(TEXT("tessa")), TEXT("TessaDelivery")); });
	Add(TEXT("elara"), [this](float T) { Place(FVector(530.f, -98.f, 1.6f), 0.f); return Talk(FindSpeaker(TEXT("villager")), TEXT("ElaraDelivery")); });
	Add(TEXT("deliveries check"), [this, Done](float T)
	{
		Check(TEXT("DeliveriesDone"), Done(TEXT("morning_deliveries"), TEXT("tavern")) && Done(TEXT("morning_deliveries"), TEXT("tessa")) && Done(TEXT("morning_deliveries"), TEXT("cliffs")),
			TEXT("tavern, Tessa, Cloud Edge"));
		return true;
	});
	Add(TEXT("maren return"), [this](float T) { Place(FVector(51.f, 58.f, 1.2f), 135.f); return Talk(FindSpeaker(TEXT("maren")), TEXT("MarenReturn")); });
	Add(TEXT("sunset check"), [this, Story, Quest, Tod](float T)
	{
		if (T == 0.f)
		{
			Check(TEXT("SunsetAndDeed"), Quest(TEXT("morning_deliveries")) == ELSQuestState::Complete && Story->HasFlag(TEXT("deed_received"))
				&& Quest(TEXT("hidden_workshop")) == ELSQuestState::Active && Tod() == TEXT("Sunset") && Conversations.Contains(TEXT("maren_deed")),
				FString::Printf(TEXT("time %s, deed %d"), *Tod(), Story->HasFlag(TEXT("deed_received")) ? 1 : 0));
			ShotFrom(FVector(-60.f * CmPerM, -40.f * CmPerM, 30.f * CmPerM), FRotator(-8.f, 45.f, 0.f));
		}
		if (At(2.f))
		{
			Shot(TEXT("sunset"));
		}
		if (T > 2.6f)
		{
			GetWorld()->GetFirstPlayerController()->SetViewTarget(Kieran());
			return true;
		}
		return false;
	});
	Add(TEXT("save and load"), [this, Story, Quest, Tod](float T)
	{
		const bool bSaved = Story->SaveToSlot(SaveSlot);
		Story->SetFlag(TEXT("bot_marker"));
		Story->SetTimeOfDay(TEXT("Morning"));
		const bool bLoaded = Story->LoadFromSlot(SaveSlot);
		Director()->ApplyStoryState();
		Check(TEXT("SaveAndLoad"), bSaved && bLoaded && !Story->HasFlag(TEXT("bot_marker")) && Story->HasFlag(TEXT("deed_received"))
			&& Quest(TEXT("hidden_workshop")) == ELSQuestState::Active && Tod() == TEXT("Sunset"),
			FString::Printf(TEXT("saved %d, loaded %d, time %s"), bSaved ? 1 : 0, bLoaded ? 1 : 0, *Tod()));
		return true;
	});
	Add(TEXT("elias notes"), [this](float T)
	{
		TArray<ALSJournalPickup*> Notes;
		for (TActorIterator<ALSJournalPickup> It(GetWorld()); It; ++It)
		{
			Notes.Add(*It);
		}
		if (NoteIndex >= Notes.Num())
		{
			return true;
		}
		if (FMath::Fmod(T, 0.5f) < GetWorld()->GetDeltaSeconds())
		{
			ALSJournalPickup* N = Notes[NoteIndex++];
			Place(N->GetActorLocation() / CmPerM + FVector(0.f, 0.f, 1.f), 0.f);
			if (ULSInteractableComponent* I = N->FindComponentByClass<ULSInteractableComponent>())
			{
				I->Interact(Kieran());
			}
		}
		return false;
	});
	Add(TEXT("notes check"), [this, Quest](float T)
	{
		Check(TEXT("EliasWasHere"), Quest(TEXT("elias_was_here")) == ELSQuestState::Complete, FString::Printf(TEXT("%d notes found"), NoteIndex));
		return true;
	});

	// ---- Chapter 2: The Hidden Workshop
	Add(TEXT("workshop door"), [this](float T)
	{
		const FTransform Door = Director()->DoorSpawn;
		Place(Door.GetLocation() / CmPerM, Door.Rotator().Yaw);
		return Talk(FindByPrompt(TEXT("Enter workshop")), TEXT("EntersWorkshop"));
	});
	Add(TEXT("workshop check"), [this, Story, Done, Tod](float T)
	{
		if (T == 0.f)
		{
			const float Dist = FVector::Dist(Kieran()->GetActorLocation(), Director()->InteriorSpawn.GetLocation());
			Check(TEXT("EntersWorkshop"), Done(TEXT("hidden_workshop"), TEXT("enter")) && Dist < 500.f && Tod() == TEXT("Night")
				&& Story->GetState().Discovered.Contains(TEXT("workshop")), FString::Printf(TEXT("%.0f m from the interior spawn, time %s"), Dist / CmPerM, *Tod()));
			Kieran()->SetActorRotation(FRotator(0.f, 20.f, 0.f));
			GetWorld()->GetFirstPlayerController()->SetControlRotation(FRotator(-12.f, 20.f, 0.f));
		}
		if (At(1.5f))
		{
			Shot(TEXT("workshop"));
		}
		if (At(2.f))
		{
			// Brindle at night, seen from below the Bluff.
			ShotFrom(FVector(170.f * CmPerM, 470.f * CmPerM, 45.f * CmPerM), FRotator(-12.f, 125.f, 0.f));
		}
		if (At(4.f))
		{
			Shot(TEXT("night"));
		}
		if (T > 4.6f)
		{
			GetWorld()->GetFirstPlayerController()->SetViewTarget(Kieran());
			return true;
		}
		return false;
	});
	for (const TCHAR* Prompt : { TEXT("Study the maps"), TEXT("Look at the sketches"), TEXT("Read the weather logs"), TEXT("Look at the portrait"), TEXT("Examine the instruments") })
	{
		Add(Prompt, [this, Prompt](float T) { return Talk(FindByPrompt(Prompt), TEXT("WorkshopInspect")); });
	}
	Add(TEXT("search check"), [this, Story, Done](float T)
	{
		Check(TEXT("SearchesWorkshop"), Done(TEXT("hidden_workshop"), TEXT("search")) && Conversations.Contains(TEXT("search_done")), TEXT("maps, sketches and notes"));
		return true;
	});
	Add(TEXT("compartment"), [this](float T) { return Talk(FindByPrompt(TEXT("Lift the floorboard")), TEXT("Compartment")); });
	Add(TEXT("final entry"), [this](float T) { return Talk(FindByPrompt(TEXT("Lift the floorboard")), TEXT("FinalEntry")); });
	Add(TEXT("dawn check"), [this, Story, Quest, Tod](float T)
	{
		const float Dist = FVector::Dist(Kieran()->GetActorLocation(), Director()->DoorSpawn.GetLocation());
		Check(TEXT("CompassAwakens"), Story->HasFlag(TEXT("compass_active")) && Story->GetItemCount(TEXT("brass_compass")) == 1
			&& Quest(TEXT("hidden_workshop")) == ELSQuestState::Complete && Conversations.Contains(TEXT("compass_awakens")), TEXT("compass, Chapter 2 complete"));
		Check(TEXT("NextMorning"), Tod() == TEXT("Dawn") && Story->GetChapter() == 3 && Quest(TEXT("into_the_clouds")) == ELSQuestState::Active && Dist < 300.f,
			FString::Printf(TEXT("time %s, chapter %d, %.0f m from the workshop door"), *Tod(), Story->GetChapter(), Dist / CmPerM));
		return true;
	});

	// ---- Chapter 3: Into the Clouds
	Add(TEXT("compass"), [this](float T)
	{
		ALSPlayerCharacter* K = Kieran();
		if (T == 0.f)
		{
			Place(FVector(55.f, 640.f, 21.2f), 90.f);
			K->Compass->OnPulse.AddUniqueDynamic(this, &ALSBrindleCheck::HandlePulse);
			K->Compass->Pulse();
		}
		if (At(0.8f))
		{
			Check(TEXT("CompassPulse"), Pulses == 1, FString::Printf(TEXT("%d pulse"), Pulses));
			Shot(TEXT("compass"));
		}
		return T > 1.4f;
	});
	Add(TEXT("piko meeting"), [this](float T)
	{
		bool bPikoPerched = false;
		for (TActorIterator<APikoCompanion> It(GetWorld()); It; ++It)
		{
			bPikoPerched = !It->IsHidden() && FVector::Dist(It->GetActorLocation(), Director()->PikoPerch) < 100.f;
		}
		Check(TEXT("PikoWaitsOnGlider"), bPikoPerched && Director()->GliderProp && !Director()->GliderProp->IsHidden() && !Kieran()->Glider->IsGliding(), TEXT("Piko sitting on the glider"));
		Place(FVector(48.f, 658.f, 21.2f), 90.f);
		return Talk(FindByPrompt(TEXT("Approach")), TEXT("PikoMeeting"));
	});
	Add(TEXT("piko check"), [this, Story, Done](float T)
	{
		if (T == 0.f)
		{
			bool bFollowing = false;
			for (TActorIterator<APikoCompanion> It(GetWorld()); It; ++It)
			{
				bFollowing = !It->IsHidden() && It->IsActorTickEnabled();
			}
			Check(TEXT("PikoJoins"), Story->HasFlag(TEXT("piko_joined")) && Story->HasFlag(TEXT("has_glider")) && Kieran()->Glider->bHasGlider && bFollowing
				&& Done(TEXT("into_the_clouds"), TEXT("bluff")), TEXT("Piko follows, glider unlocked"));
			Kieran()->SetActorRotation(FRotator(0.f, 60.f, 0.f));
			GetWorld()->GetFirstPlayerController()->SetControlRotation(FRotator(-8.f, 60.f, 0.f));
		}
		if (At(2.f))
		{
			Shot(TEXT("dawn_launch"));
		}
		return T > 2.5f;
	});
	Add(TEXT("glide to the fog"), [this, Story](float T)
	{
		ALSPlayerCharacter* K = Kieran();
		if (T == 0.f)
		{
			Place(FVector(60.f, 668.f, 21.4f), 90.f);
			GlideStart = K->GetActorLocation();
			bDeployed = false;
		}
		// Talk through anything said in flight (launch_ready, piko_found_wind).
		if (Story->IsInDialogue())
		{
			AdvanceTimer += GetWorld()->GetDeltaSeconds();
			if (AdvanceTimer > 0.6f)
			{
				AdvanceTimer = 0.f;
				Story->AdvanceDialogue();
			}
		}
		if (!K->Glider->IsGliding() && !bDeployed)
		{
			K->Traversal->SetMoveInput(FVector(0.f, 1.f, 0.f), 0.f, 1.f);
			K->AddMovementInput(FVector(0.f, 1.f, 0.f));
			if (K->GetCharacterMovement()->IsFalling() && K->GetActorLocation().Z < GlideStart.Z - 2.f * CmPerM)
			{
				K->DoJumpStart();
				bDeployed = K->Glider->IsGliding();
			}
		}
		LogTimer += GetWorld()->GetDeltaSeconds();
		if (LogTimer > 5.f)
		{
			LogTimer = 0.f;
			UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE flight at %s, gliding %d, airspeed %.1f m/s"), *(K->GetActorLocation() / CmPerM).ToCompactString(),
				K->Glider->IsGliding() ? 1 : 0, K->Glider->GetAirspeed());
		}
		return Story->HasFlag(TEXT("demo_complete")) || T > 90.f;
	});
	Add(TEXT("fog end"), [this, Story, Quest, Done](float T)
	{
		if (T == 0.f)
		{
			const FVector P = Kieran()->GetActorLocation() / CmPerM;
			Check(TEXT("PikoRevealsUpdraft"), Story->HasFlag(TEXT("revealed_wind_1")) && Conversations.Contains(TEXT("piko_found_wind")), TEXT("hidden updraft and piko_found_wind"));
			Check(TEXT("GlidesToTheFog"), Story->HasFlag(TEXT("reached_fog")) && Done(TEXT("into_the_clouds"), TEXT("glide")) && P.Y > 1400.f,
				FString::Printf(TEXT("Kieran at %s, %.0f m east of the Bluff"), *P.ToCompactString(), P.Y - GlideStart.Y / CmPerM));
			Check(TEXT("DemoComplete"), Story->HasFlag(TEXT("demo_complete")) && Quest(TEXT("into_the_clouds")) == ELSQuestState::Complete
				&& Quest(TEXT("morning_deliveries")) == ELSQuestState::Complete && Quest(TEXT("hidden_workshop")) == ELSQuestState::Complete
				&& Quest(TEXT("elias_was_here")) == ELSQuestState::Complete, TEXT("all four quests complete"));
		}
		if (At(5.f))
		{
			Check(TEXT("EndView"), Director()->HasDemoEnded() && Director()->GetFogAmount() > 0.9f, FString::Printf(TEXT("fog %.2f"), Director()->GetFogAmount()));
			Shot(TEXT("fog_end"));
		}
		return T > 5.6f;
	});
	Add(TEXT("summary"), [this](float T)
	{
		UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE_SUMMARY %d/%d passed"), Passed, Total);
		GetWorld()->GetFirstPlayerController()->ConsoleCommand(TEXT("quit"));
		return true;
	});
}

void ALSBrindleCheck::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Kieran() || !Story || !Director() || Index >= Actions.Num())
	{
		return;
	}
	if (bWaiting)
	{
		// Between actions: talk through any conversation and let the story director finish (fades, queued lines).
		if (Story->IsInDialogue())
		{
			AdvanceTimer += DeltaSeconds;
			if (AdvanceTimer >= 0.5f)
			{
				AdvanceTimer = 0.f;
				Story->AdvanceDialogue();
			}
			WaitTime = 0.f;
			return;
		}
		WaitTime = IsIdle() ? WaitTime + DeltaSeconds : 0.f;
		if (WaitTime < 0.4f)
		{
			return;
		}
		bWaiting = false;
		StepTime = 0.f;
		CurStepTime = -1.f;
		UE_LOG(LogTemp, Display, TEXT("LS_BRINDLE step %s"), *Actions[Index].Name);
	}
	const float T = StepTime;
	LastStepTime = CurStepTime;
	CurStepTime = T;
	StepTime += DeltaSeconds;
	if (Actions[Index].Run(T))
	{
		++Index;
		bWaiting = true;
		WaitTime = 0.f;
	}
}

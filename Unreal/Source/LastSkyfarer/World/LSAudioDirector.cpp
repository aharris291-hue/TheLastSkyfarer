// The Last Skyfarer: story-driven sounds.

#include "LSAudioDirector.h"

#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "LSCompassComponent.h"
#include "LSPlayerCharacter.h"
#include "LSStorySubsystem.h"
#include "PikoCompanion.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundMix.h"

namespace
{
	template <typename T>
	T* LoadAudio(const TCHAR* Name)
	{
		return LoadObject<T>(nullptr, *FString::Printf(TEXT("/Game/LastSkyfarer/Audio/%s"), Name));
	}
}

ALSAudioDirector::ALSAudioDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.25f;
}

void ALSAudioDirector::BeginPlay()
{
	Super::BeginPlay();
	Discovery = LoadAudio<USoundBase>(TEXT("Stingers/stinger_discovery.stinger_discovery"));
	QuestStart = LoadAudio<USoundBase>(TEXT("Stingers/stinger_quest_start.stinger_quest_start"));
	QuestDone = LoadAudio<USoundBase>(TEXT("Stingers/stinger_quest_done.stinger_quest_done"));
	JournalStinger = LoadAudio<USoundBase>(TEXT("Stingers/stinger_journal.stinger_journal"));
	JournalPage = LoadAudio<USoundBase>(TEXT("UI/journal_page.journal_page"));
	JournalInk = LoadAudio<USoundBase>(TEXT("UI/journal_ink.journal_ink"));
	CompassPulse = LoadAudio<USoundBase>(TEXT("UI/compass_pulse.compass_pulse"));
	CompassAwaken = LoadAudio<USoundBase>(TEXT("UI/compass_awaken.compass_awaken"));
	DuckMix = LoadAudio<USoundMix>(TEXT("Mix/SMix_DialogueDuck.SMix_DialogueDuck"));

	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnQuestChanged.AddUniqueDynamic(this, &ALSAudioDirector::HandleQuestChanged);
		Story->OnJournalAdded.AddUniqueDynamic(this, &ALSAudioDirector::HandleJournalAdded);
		Story->OnDialogueLine.AddUniqueDynamic(this, &ALSAudioDirector::HandleDialogueLine);
		Story->OnDialogueEnded.AddUniqueDynamic(this, &ALSAudioDirector::HandleDialogueEnded);
		Story->OnStoryEvent.AddUniqueDynamic(this, &ALSAudioDirector::HandleStoryEvent);
	}
}

bool ALSAudioDirector::Play(USoundBase* Sound, float Volume)
{
	if (Sound)
	{
		UGameplayStatics::PlaySound2D(this, Sound, Volume);
	}
	return Sound != nullptr;
}

void ALSAudioDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story)
	{
		return;
	}
	// A new place on the map: a short rising bell phrase.
	const int32 Places = Story->GetState().Discovered.Num();
	if (KnownPlaces >= 0 && Places > KnownPlaces)
	{
		StingersPlayed += Play(Discovery, 0.7f) ? 1 : 0;
	}
	KnownPlaces = Places;

	if (!bCompassBound)
	{
		const APlayerController* PC = GetWorld()->GetFirstPlayerController();
		if (const ALSPlayerCharacter* K = PC ? Cast<ALSPlayerCharacter>(PC->GetPawn()) : nullptr)
		{
			K->Compass->OnPulse.AddUniqueDynamic(this, &ALSAudioDirector::HandleCompassPulse);
			bCompassBound = true;
		}
	}
}

void ALSAudioDirector::HandleQuestChanged(FName QuestId, ELSQuestState State)
{
	if (State == ELSQuestState::Active)
	{
		StingersPlayed += Play(QuestStart, 0.6f) ? 1 : 0;
	}
	else if (State == ELSQuestState::Complete)
	{
		StingersPlayed += Play(QuestDone, 0.7f) ? 1 : 0;
	}
}

void ALSAudioDirector::HandleJournalAdded(FName EntryId)
{
	Play(JournalPage, 0.7f);
	Play(JournalInk, 0.4f);
	Play(JournalStinger, 0.4f);
}

void ALSAudioDirector::HandleDialogueLine(FName ConversationId, const FLSDialogueLine& Line)
{
	if (!bDucked && DuckMix)
	{
		UGameplayStatics::PushSoundMixModifier(this, DuckMix);
		bDucked = true;
	}
}

void ALSAudioDirector::HandleDialogueEnded(FName ConversationId)
{
	if (bDucked && DuckMix)
	{
		UGameplayStatics::PopSoundMixModifier(this, DuckMix);
		bDucked = false;
	}
}

void ALSAudioDirector::HandleStoryEvent(FName EventId)
{
	if (EventId == TEXT("compass_awakens"))
	{
		Play(CompassAwaken, 0.9f);
	}
	else if (EventId == TEXT("piko_joins"))
	{
		for (TActorIterator<APikoCompanion> It(GetWorld()); It; ++It)
		{
			It->Chirp(true);
		}
	}
}

void ALSAudioDirector::HandleCompassPulse(const FLSCompassReading& Reading)
{
	Play(CompassPulse, 0.7f);
}

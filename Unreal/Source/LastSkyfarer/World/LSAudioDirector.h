// The Last Skyfarer: story-driven sounds (stingers, journal and compass sounds, dialogue ducking).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSNarrativeTypes.h"
#include "LSAudioDirector.generated.h"

class USoundBase;
class USoundMix;

/**
 * Listens to the story and plays the small sounds that mark moments: a bell phrase for a new place, a quest
 * starting or finishing, paper and ink for a journal entry, a brass shimmer for each compass pulse (a bigger one
 * when it first wakes), Piko's trill when he joins. While anyone speaks, music and ambience duck a little.
 * Spawned once per game level.
 */
UCLASS()
class LASTSKYFARER_API ALSAudioDirector : public AActor
{
	GENERATED_BODY()

public:
	ALSAudioDirector();
	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION(BlueprintPure, Category = "Audio") int32 GetStingersPlayed() const { return StingersPlayed; }
	UFUNCTION(BlueprintPure, Category = "Audio") bool IsDucking() const { return bDucked; }

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY() TObjectPtr<USoundBase> Discovery;
	UPROPERTY() TObjectPtr<USoundBase> QuestStart;
	UPROPERTY() TObjectPtr<USoundBase> QuestDone;
	UPROPERTY() TObjectPtr<USoundBase> JournalStinger;
	UPROPERTY() TObjectPtr<USoundBase> JournalPage;
	UPROPERTY() TObjectPtr<USoundBase> JournalInk;
	UPROPERTY() TObjectPtr<USoundBase> CompassPulse;
	UPROPERTY() TObjectPtr<USoundBase> CompassAwaken;
	UPROPERTY() TObjectPtr<USoundMix> DuckMix;

	int32 KnownPlaces = -1;
	int32 StingersPlayed = 0;
	bool bDucked = false;
	bool bCompassBound = false;

	/** True if the sound exists (and was played). */
	bool Play(USoundBase* Sound, float Volume = 1.f);

	UFUNCTION() void HandleQuestChanged(FName QuestId, ELSQuestState State);
	UFUNCTION() void HandleJournalAdded(FName EntryId);
	UFUNCTION() void HandleDialogueLine(FName ConversationId, const FLSDialogueLine& Line);
	UFUNCTION() void HandleDialogueEnded(FName ConversationId);
	UFUNCTION() void HandleStoryEvent(FName EventId);
	UFUNCTION() void HandleCompassPulse(const struct FLSCompassReading& Reading);
};

// The Last Skyfarer: scripted Milestone A run on Brindle Isle (-LSBrindleCheck).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSBrindleCheck.generated.h"

class ACameraActor;
class ALSBrindleStory;
class ALSPlayerCharacter;
class ULSInteractableComponent;

/**
 * Plays the whole Milestone A story as a bot, in the order of Unreal/Tools/validate_narrative.py: the opening
 * on the Upper Cliffs, the village and Rowan, the map, Morning Deliveries, the sunset and the deed, a save and
 * load, Elias's notes, the workshop at night, the search, the compartment and final entry, the compass at dawn,
 * Piko and the glider, and the glide east to the fog. Logs "LS_BRINDLE <check> PASS/FAIL", saves screenshots
 * to Saved/Screenshots and quits.
 */
UCLASS()
class LASTSKYFARER_API ALSBrindleCheck : public AActor
{
	GENERATED_BODY()

public:
	ALSBrindleCheck();
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	struct FAction
	{
		FString Name;
		TFunction<bool(float)> Run; // returns true when done
	};
	TArray<FAction> Actions;
	int32 Index = 0;
	float StepTime = 0.f;
	float LastStepTime = -1.f;
	float CurStepTime = -1.f;
	float WaitTime = 0.f;
	float AdvanceTimer = 0.f;
	bool bWaiting = false;
	int32 Passed = 0;
	int32 Total = 0;
	int32 Pulses = 0;
	int32 NoteIndex = 0;
	float LogTimer = 0.f;
	FVector GlideStart = FVector::ZeroVector;
	bool bDeployed = false;
	FName RowanConversation;
	TArray<FName> Conversations;

	UPROPERTY() TObjectPtr<ACameraActor> ShotCamera;

	void Build();
	void Add(const FString& Name, TFunction<bool(float)> Run);
	void Check(const TCHAR* Name, bool bPass, const FString& Detail);
	void Shot(const TCHAR* Name);
	void ShotFrom(const FVector& Where, const FRotator& Rot);
	void Place(const FVector& WhereM, float Yaw);
	bool Talk(ULSInteractableComponent* Target, const TCHAR* What);
	bool IsIdle() const;
	/** True on the one tick where the current action's time passes Seconds. */
	bool At(float Seconds) const;

	ALSPlayerCharacter* Kieran() const;
	ALSBrindleStory* Director() const;
	ULSInteractableComponent* FindByPrompt(const FString& Prompt) const;
	ULSInteractableComponent* FindSpeaker(FName Speaker) const;

	UFUNCTION() void HandlePulse(const struct FLSCompassReading& Reading);
	UFUNCTION() void HandleLine(FName ConversationId, const struct FLSDialogueLine& Line);
};

// The Last Skyfarer: scripted UI and story playthrough of L_SystemsTest (-LSPlaythrough).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSPlaythroughCheck.generated.h"

class ALSHUD;
class ALSPlayerCharacter;

/**
 * Plays the opening, talks to the test NPC, picks up an Elias note, opens the journal and the pause
 * menu (save), taking screenshots of the dialogue box and journal. Logs "LS_PLAY <check> PASS/FAIL" and quits.
 */
UCLASS()
class LASTSKYFARER_API ALSPlaythroughCheck : public AActor
{
	GENERATED_BODY()

public:
	ALSPlaythroughCheck();
	virtual void Tick(float DeltaSeconds) override;

private:
	int32 Step = 0;
	float StepTime = 0.f;
	float AdvanceTimer = 0.f;
	int32 Passed = 0;
	int32 Total = 0;
	int32 Toasts = 0;
	FString LastToast;
	bool bShotTaken = false;

	ALSPlayerCharacter* Kieran() const;
	ALSHUD* HUD() const;
	void Check(const TCHAR* Name, bool bPass, const FString& Detail);
	void Shot(const TCHAR* Name);
	void Next();
	/** Advances the running conversation every 0.6 s; returns true once it has ended. */
	bool PumpDialogue(float Dt);

	UFUNCTION() void HandleNotify(const FText& Message);
};

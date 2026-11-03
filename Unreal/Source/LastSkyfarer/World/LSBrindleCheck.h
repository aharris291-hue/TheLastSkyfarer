// The Last Skyfarer: scripted check of the Brindle Isle greybox (-LSBrindleCheck).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSBrindleCheck.generated.h"

class ACameraActor;

/**
 * Overview shot from above, the opening on the Upper Cliffs, the village square, a talk with Rowan, the map screen with a
 * pin, a compass pulse, and a glide off Old Cartographer's Bluff. Logs "LS_BRINDLE <check> PASS/FAIL",
 * saves screenshots to Saved/Screenshots and quits.
 */
UCLASS()
class LASTSKYFARER_API ALSBrindleCheck : public AActor
{
	GENERATED_BODY()

public:
	ALSBrindleCheck();
	virtual void Tick(float DeltaSeconds) override;

private:
	int32 Step = 0;
	float StepTime = 0.f;
	float AdvanceTimer = 0.f;
	int32 Passed = 0;
	int32 Total = 0;
	int32 Pulses = 0;
	bool bShot = false;
	FVector GlideStart = FVector::ZeroVector;
	FName RowanConversation;

	UPROPERTY() TObjectPtr<ACameraActor> OverviewCamera;

	void Check(const TCHAR* Name, bool bPass, const FString& Detail);
	void Shot(const TCHAR* Name);
	void Next();
	bool PumpDialogue(float Dt);

	UFUNCTION() void HandlePulse(const struct FLSCompassReading& Reading);
	UFUNCTION() void HandleLine(FName ConversationId, const struct FLSDialogueLine& Line);
};

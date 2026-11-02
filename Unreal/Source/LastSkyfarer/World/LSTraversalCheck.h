// The Last Skyfarer: end-to-end traversal check run in a real game world (-LSTraversalCheck).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSTraversalCheck.generated.h"

class ALSPlayerCharacter;

/**
 * Spawns three test blocks next to the player start, then drives Kieran through a mantle, a ledge
 * hang with pull-up and a climb, logging "LS_TRAV <case> PASS/FAIL" lines, and quits.
 */
UCLASS()
class LASTSKYFARER_API ALSTraversalCheck : public AActor
{
	GENERATED_BODY()

public:
	ALSTraversalCheck();
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	int32 Step = 0;
	float StepTime = 0.f;
	int32 Passed = 0;
	int32 Total = 0;
	bool bHangSeen = false;

	ALSPlayerCharacter* Kieran() const;
	float Feet() const;
	void SpawnBlock(const FVector& Center, const FVector& Size, bool bClimbable);
	void Place(const FVector& Feet);
	void Push(const FVector& Dir, float StickRight, float StickForward);
	void Report(const TCHAR* Case, bool bPass, const FString& Detail);
	void NextStep();
};

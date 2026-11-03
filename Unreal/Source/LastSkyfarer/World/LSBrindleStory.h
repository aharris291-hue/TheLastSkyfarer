// The Last Skyfarer: Brindle Isle story director (the level side of the Milestone A story).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSBrindleStory.generated.h"

class ACameraActor;
class APikoCompanion;

/**
 * Handles the story events the Brindle Isle levels raised in the Godot demo (windrest.gd, workshop.gd):
 * the sunset fade before the deed, entering and leaving the workshop, the compass awakening, the next
 * morning, Piko joining and unlocking the glider, Piko's first hidden wind, the fog and the demo end.
 * Conversations it starts wait until no other conversation is running. Placed once by the level script.
 */
UCLASS()
class LASTSKYFARER_API ALSBrindleStory : public AActor
{
	GENERATED_BODY()

public:
	ALSBrindleStory();
	virtual void Tick(float DeltaSeconds) override;

	/** Where Kieran stands inside the workshop after entering. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FTransform InteriorSpawn;

	/** Where Kieran stands outside the workshop door after leaving it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FTransform DoorSpawn;

	/** Camera for the demo's last view (the island silhouette in the fog). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FTransform EndView;

	/** Piko waits here, sitting on the glider, on the morning of Chapter 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FVector PikoPerch = FVector::ZeroVector;

	/** The glider at the Bluff edge, shown from the compass awakening until Piko joins. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TObjectPtr<AActor> GliderProp;

	/** Blocks the Bluff edge until Kieran has the glider. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TObjectPtr<AActor> EdgeWall;

	/** The glider, journal and goggles in the workshop floor, shown once the compartment is open. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TArray<TObjectPtr<AActor>> CompartmentProps;

	/** The fog thickens between these east (+Y) distances, cm, as Kieran nears the place the wind refuses. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story|Fog")
	float FogStartY = 125000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story|Fog")
	float FogFullY = 155000.f;

	/** Low-contrast white and teal (STYLE_GUIDE colour script 6). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story|Fog")
	FLinearColor FogColor = FLinearColor(0.78f, 0.9f, 0.9f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story|Fog")
	float FogDensity = 0.06f;

	/** Re-applies everything that depends on story flags (after loading a save, for example). */
	UFUNCTION(BlueprintCallable, Category = "Story")
	void ApplyStoryState();

	UFUNCTION(BlueprintPure, Category = "Story")
	bool IsBusy() const { return Steps.Num() > 0; }

	UFUNCTION(BlueprintPure, Category = "Story")
	bool HasDemoEnded() const { return bDemoEnded; }

	UFUNCTION(BlueprintPure, Category = "Story")
	float GetFogAmount() const { return FogAmount; }

protected:
	virtual void BeginPlay() override;

private:
	struct FStep
	{
		float Delay = 0.f;
		FName Conversation;
		TFunction<void()> Run;
	};
	TArray<FStep> Steps;

	bool bDemoEnded = false;
	float FogAmount = 0.f;
	float BaseFogDensity = -1.f;
	FLinearColor BaseFogColor;

	UPROPERTY() TObjectPtr<APikoCompanion> Piko;
	UPROPERTY() TObjectPtr<ACameraActor> EndCamera;

	void Queue(FName Conversation, float Delay = 0.f);
	void QueueRun(TFunction<void()> Run, float Delay = 0.f);
	void FadeThrough(TFunction<void()> Middle, const FText& Caption = FText::GetEmpty());
	void Notify(const FText& Message);
	void Teleport(const FTransform& Where);
	void UpdateFog();
	void FindPiko();

	UFUNCTION() void HandleStoryEvent(FName EventId);
	UFUNCTION() void HandleFlagChanged(FName Flag, bool bSet);
	UFUNCTION() void HandlePikoSensed(int32 NumRevealed);
};

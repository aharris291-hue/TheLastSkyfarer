// The Last Skyfarer: a Beacon in the world (GDD 8). Placeholder rings; the Synchronize step
// is the ring puzzle. Level scripts and Sequencer hook the stage events.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSRestorationTypes.h"
#include "LSBeacon.generated.h"

class ULSInteractableComponent;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLSOnBeaconStage, FName, BeaconId, ELSRestorationStage, Stage);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLSOnRingTurned, int32, Ring, bool, bAligned);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnBeaconRegionalReaction, FName, BeaconId);

UCLASS(Blueprintable)
class LASTSKYFARER_API ALSBeacon : public AActor
{
	GENERATED_BODY()

public:
	ALSBeacon();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Beacon")
	TObjectPtr<ULSRestorationDef> Definition;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Beacon")
	TObjectPtr<UStaticMeshComponent> Pillar;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Beacon")
	TArray<TObjectPtr<UStaticMeshComponent>> RingMeshes;

	/** Starts the ring puzzle when the Beacon is Restored but not yet Synchronized. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Beacon")
	TObjectPtr<ULSInteractableComponent> Interactable;

	UFUNCTION(BlueprintPure, Category = "Beacon") ELSRestorationStage GetStage() const;
	UFUNCTION(BlueprintCallable, Category = "Beacon") bool AdvanceTo(ELSRestorationStage Stage);

	UFUNCTION(BlueprintPure, Category = "Beacon") bool IsSynchronizing() const { return bSynchronizing; }
	UFUNCTION(BlueprintCallable, Category = "Beacon") bool BeginSynchronize();
	UFUNCTION(BlueprintCallable, Category = "Beacon") void CancelSynchronize();
	/** Turns a ring one glyph left (-1) or right (+1). Solving all rings advances to Synchronized. */
	UFUNCTION(BlueprintCallable, Category = "Beacon") bool TurnRing(int32 Ring, int32 Direction);

	/** Call when the regional reaction cinematic has finished: advances to Reacted, then Advanced. */
	UFUNCTION(BlueprintCallable, Category = "Beacon") void FinishRegionalReaction();

	UFUNCTION(BlueprintPure, Category = "Beacon") const FLSRingPuzzle& GetPuzzle() const { return Puzzle; }

	UPROPERTY(BlueprintAssignable, Category = "Beacon") FLSOnBeaconStage OnStageChanged;
	UPROPERTY(BlueprintAssignable, Category = "Beacon") FLSOnRingTurned OnRingTurned;
	/** Play the pillar of light, the island rise and the new routes; then call FinishRegionalReaction. */
	UPROPERTY(BlueprintAssignable, Category = "Beacon") FLSOnBeaconRegionalReaction OnRegionalReaction;

	/** Degrees per second the rings ease towards their glyph position. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Beacon")
	float RingTurnSpeed = 180.f;

	virtual void Tick(float DeltaTime) override;

protected:
	virtual void BeginPlay() override;
	virtual void OnConstruction(const FTransform& Transform) override;

private:
	UFUNCTION() void HandleInteracted(AActor* By);
	FName BeaconId() const;
	void RefreshInteractable();

	FLSRingPuzzle Puzzle;
	bool bSynchronizing = false;
};

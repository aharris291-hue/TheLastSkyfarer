// The Last Skyfarer: restoration framework (GDD 8). Six stages per Beacon or restorable
// system; every stage is a story flag, so progress is saved with the story and usable in
// conditions ("beacon_veilmist_synchronized").

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "LSNarrativeTypes.h"
#include "LSRestorationTypes.generated.h"

class ULSStorySubsystem;

UENUM(BlueprintType)
enum class ELSRestorationStage : uint8
{
	Unknown,
	Discovered,		// seen from afar, logged on the map
	Investigated,	// the problem is understood
	Restored,		// the local challenge is done
	Synchronized,	// the ring alignment is done
	Reacted,		// the regional reaction cinematic has played
	Advanced		// story flags, routes and fast travel unlocked
};

USTRUCT(BlueprintType)
struct FLSRingDef
{
	GENERATED_BODY()

	/** Glyph positions around the ring. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration", meta = (ClampMin = "2"))
	int32 NumGlyphs = 8;

	/** Position the ring starts at. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration")
	int32 Start = 0;

	/** Position that matches the compass. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restoration")
	int32 Target = 0;
};

/** The Synchronize step: turn each ring until its glyph matches. No fail state (GDD 8.4). */
USTRUCT(BlueprintType)
struct LASTSKYFARER_API FLSRingPuzzle
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Restoration")
	TArray<FLSRingDef> Rings;

	UPROPERTY(BlueprintReadOnly, Category = "Restoration")
	TArray<int32> Positions;

	void Reset(const TArray<FLSRingDef>& InRings);
	/** Turns a ring by Steps (negative = back), wrapping. Returns false for a bad index. */
	bool Rotate(int32 Ring, int32 Steps);
	bool IsRingAligned(int32 Ring) const;
	bool IsSolved() const;
};

/** One Beacon or restorable system. Create one data asset per Beacon. */
UCLASS(BlueprintType)
class LASTSKYFARER_API ULSRestorationDef : public UPrimaryDataAsset
{
	GENERATED_BODY()

public:
	/** e.g. veilmist. Flags are beacon_<Id>_<stage>. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Restoration")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Restoration")
	FText DisplayName;

	/** Three rings by default (GDD 8.4). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Restoration")
	TArray<FLSRingDef> Rings;

	/** Actions per stage, run when the stage is reached (e.g. journal entries, chapter, quest steps). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Restoration")
	TMap<ELSRestorationStage, FLSStoryActionList> StageActions;
};

UCLASS()
class LASTSKYFARER_API ULSRestorationLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Flag set when Id reaches Stage, e.g. beacon_veilmist_restored. None for Unknown. */
	UFUNCTION(BlueprintPure, Category = "Restoration")
	static FName StageFlag(FName Id, ELSRestorationStage Stage);

	/** Highest stage whose flag is set. */
	static ELSRestorationStage GetStage(const ULSStorySubsystem& Story, FName Id);

	/**
	 * Moves Id forward to Stage, setting the flag of every stage passed and running each
	 * stage's actions once, in order. Never moves backwards. Returns true if anything changed.
	 */
	static bool AdvanceTo(ULSStorySubsystem& Story, FName Id, ELSRestorationStage Stage,
		const TMap<ELSRestorationStage, FLSStoryActionList>* StageActions = nullptr);
};

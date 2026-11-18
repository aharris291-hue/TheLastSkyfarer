// The Last Skyfarer: things that appear on the map and that the compass can point to (GDD 3, 9).

#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "Subsystems/WorldSubsystem.h"
#include "LSNarrativeTypes.h"
#include "LSMapMarkerComponent.generated.h"

class ULSStorySubsystem;

UENUM(BlueprintType)
enum class ELSMapMarkerKind : uint8
{
	/** A named place (LocationId); inked once discovered, pencilled when heard of. */
	Landmark,
	/** Where a quest objective happens (QuestId + ObjectiveId); shown while that objective is open. */
	Objective,
	/** A fast travel Beacon (shown once its Beacon is Advanced). */
	FastTravel
};

/** One state of a marker, for the map screen and the compass. */
USTRUCT(BlueprintType)
struct FLSMapMarkerView
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Map") ELSMapMarkerKind Kind = ELSMapMarkerKind::Landmark;
	UPROPERTY(BlueprintReadOnly, Category = "Map") FVector WorldLocation = FVector::ZeroVector;
	UPROPERTY(BlueprintReadOnly, Category = "Map") FText Label;
	UPROPERTY(BlueprintReadOnly, Category = "Map") ELSMapKnowledge Knowledge = ELSMapKnowledge::Known;
	/** Objective markers of the tracked quest are highlighted. */
	UPROPERTY(BlueprintReadOnly, Category = "Map") bool bTracked = false;
};

UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API ULSMapMarkerComponent : public USceneComponent
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	ELSMapMarkerKind Kind = ELSMapMarkerKind::Landmark;

	/** Landmark: Locations.json id. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	FName LocationId;

	/** Objective: the quest and objective this marker belongs to. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	FName QuestId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	FName ObjectiveId;

	/** FastTravel: the Beacon id (shown once beacon_<id>_advanced is set). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	FName BeaconId;

	/** Extra conditions (all must pass). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	TArray<FString> VisibleIf;

	/** Label override; otherwise the location name or objective text. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	FText Label;

	/** Fills Out and returns true if the marker should be shown right now. Pure, testable. */
	bool Evaluate(const ULSStorySubsystem& Story, FLSMapMarkerView& Out) const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
};

/** Registry of map markers in the world. */
UCLASS()
class LASTSKYFARER_API ULSMapSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	void Register(ULSMapMarkerComponent* Marker) { Markers.AddUnique(Marker); }
	void Unregister(ULSMapMarkerComponent* Marker) { Markers.Remove(Marker); }

	/** Every marker the map should draw now (player pins come from ULSStorySubsystem::GetMapPins). */
	TArray<FLSMapMarkerView> GetVisibleMarkers(const ULSStorySubsystem& Story) const;

	/**
	 * What the compass pulse points at: the nearest open objective marker of the tracked quest,
	 * else the nearest open objective of any active quest, else the newest player pin.
	 * Returns false if there is nothing to point at.
	 */
	bool FindCompassTarget(const ULSStorySubsystem& Story, const FVector& From, FVector& OutTarget) const;

	UFUNCTION(BlueprintCallable, Category = "Map", meta = (DisplayName = "Get Visible Map Markers"))
	TArray<FLSMapMarkerView> K2_GetVisibleMarkers() const;

private:
	TArray<TWeakObjectPtr<ULSMapMarkerComponent>> Markers;
};

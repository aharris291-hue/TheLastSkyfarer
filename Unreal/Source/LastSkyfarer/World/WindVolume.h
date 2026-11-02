// The Last Skyfarer: wind currents, updrafts and crosswinds (GDD 2.2).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "WindVolume.generated.h"

class USplineComponent;
class UInstancedStaticMeshComponent;

UENUM(BlueprintType)
enum class EWindVolumeType : uint8
{
	/** Ribbon along the spline; pushes along it and holds altitude. */
	Current,
	/** Vertical column around the spline; adds lift. */
	Updraft,
	/** Sideways push along the actor's right vector, for hazards. */
	Crosswind
};

/** Wind sampled at a point. Velocities in cm/s. */
USTRUCT(BlueprintType)
struct LASTSKYFARER_API FWindSample
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Wind")
	FVector Velocity = FVector::ZeroVector;

	/** A current is cancelling the glider's sink. */
	UPROPERTY(BlueprintReadOnly, Category = "Wind")
	bool bHoldAltitude = false;

	UPROPERTY(BlueprintReadOnly, Category = "Wind")
	bool bInside = false;
};

/**
 * A wind volume shaped by a spline plus a radius. Hidden volumes do nothing and show nothing
 * until revealed (by Piko or the Wind Resonator).
 */
UCLASS(Blueprintable)
class LASTSKYFARER_API AWindVolume : public AActor
{
	GENERATED_BODY()

public:
	AWindVolume();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Wind")
	TObjectPtr<USplineComponent> Spline;

	/** Greybox visual: beads along the spline. Replaced by Niagara ribbons later. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Wind")
	TObjectPtr<UInstancedStaticMeshComponent> Visual;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind")
	EWindVolumeType WindType = EWindVolumeType::Current;

	/** Radius of the ribbon or column, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "50"))
	float Radius = 600.f;

	/** Push speed for currents (8-20 m/s) and crosswinds, lift for updrafts (4-9 m/s). In m/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0"))
	float Strength = 14.f;

	/** Strength falls off to this share at the edge of the radius. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0", ClampMax = "1"))
	float EdgeFalloff = 0.4f;

	/** Starts invisible and inactive until something reveals it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind")
	bool bStartsHidden = false;

	/** Spacing of the greybox beads, cm. */
	UPROPERTY(EditAnywhere, Category = "Wind|Visual")
	float BeadSpacing = 400.f;

	UFUNCTION(BlueprintCallable, Category = "Wind")
	void Reveal();

	UFUNCTION(BlueprintPure, Category = "Wind")
	bool IsActive() const { return !bStartsHidden || bRevealed; }

	UFUNCTION(BlueprintPure, Category = "Wind")
	bool IsRevealed() const { return bRevealed; }

	/** Distance from a point to the volume's spline, cm. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float DistanceToSpline(const FVector& WorldLocation) const;

	UFUNCTION(BlueprintPure, Category = "Wind")
	FWindSample SampleWind(const FVector& WorldLocation) const;

	UFUNCTION(BlueprintCallable, Category = "Wind")
	void RebuildVisual();

	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UPROPERTY(VisibleInstanceOnly, Category = "Wind")
	bool bRevealed = false;

	void UpdateVisibility();
};

/** Keeps track of wind volumes in the world so movers can query them cheaply. */
UCLASS()
class LASTSKYFARER_API UWindSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	void Register(AWindVolume* Volume) { Volumes.AddUnique(Volume); }
	void Unregister(AWindVolume* Volume) { Volumes.Remove(Volume); }

	/** Sum of all active volumes at a point. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	FWindSample SampleWind(const FVector& WorldLocation) const;

	/** Reveals hidden volumes whose spline passes within Range of the point. Returns how many were newly revealed. */
	UFUNCTION(BlueprintCallable, Category = "Wind")
	int32 RevealHiddenNear(const FVector& WorldLocation, float Range);

	/** Distance to the nearest still-hidden volume, or a huge value. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float DistanceToNearestHidden(const FVector& WorldLocation) const;

	const TArray<TWeakObjectPtr<AWindVolume>>& GetVolumes() const { return Volumes; }

private:
	TArray<TWeakObjectPtr<AWindVolume>> Volumes;
};

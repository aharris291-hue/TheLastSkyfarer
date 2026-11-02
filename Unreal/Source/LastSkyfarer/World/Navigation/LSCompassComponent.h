// The Last Skyfarer: Elias's Brass Compass (GDD 3). Pulse (F) points to the current objective
// and swings to hidden currents ("impossible routes") within range.

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LSCompassComponent.generated.h"

class ULSStorySubsystem;
class ULSMapSubsystem;
class UWindSubsystem;

USTRUCT(BlueprintType)
struct FLSCompassReading
{
	GENERATED_BODY()

	/** False when there is nothing to point at (the needle spins). */
	UPROPERTY(BlueprintReadOnly, Category = "Compass") bool bHasTarget = false;
	UPROPERTY(BlueprintReadOnly, Category = "Compass") FVector Target = FVector::ZeroVector;
	/** Horizontal direction from the player to the target (unit, Z = 0). */
	UPROPERTY(BlueprintReadOnly, Category = "Compass") FVector Direction = FVector::ZeroVector;
	/** Yaw of the needle relative to where the player faces, degrees (-180..180). */
	UPROPERTY(BlueprintReadOnly, Category = "Compass") float RelativeYaw = 0.f;
	UPROPERTY(BlueprintReadOnly, Category = "Compass") float Distance = 0.f;
	/** The needle is pulled to a hidden current instead of the objective. */
	UPROPERTY(BlueprintReadOnly, Category = "Compass") bool bImpossibleRoute = false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnCompassPulse, const FLSCompassReading&, Reading);

UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API ULSCompassComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULSCompassComponent();

	/** Story flag that unlocks the compass (set in the workshop, Ch. 2). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Compass")
	FName UnlockFlag = TEXT("compass_active");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Compass")
	float Cooldown = 3.f;

	/** Hidden currents closer than this pull the needle, cm (150 m). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Compass")
	float ImpossibleRouteRange = 15000.f;

	UFUNCTION(BlueprintPure, Category = "Compass") bool IsUnlocked() const;
	UFUNCTION(BlueprintPure, Category = "Compass") bool IsReady() const { return CooldownLeft <= 0.f; }
	UFUNCTION(BlueprintPure, Category = "Compass") float GetCooldownLeft() const { return CooldownLeft; }

	/** Pulses if unlocked and ready. Broadcasts OnPulse with the reading. Returns true if it pulsed. */
	UFUNCTION(BlueprintCallable, Category = "Compass") bool Pulse();

	UPROPERTY(BlueprintAssignable, Category = "Compass") FLSOnCompassPulse OnPulse;

	/** Pure reading, testable without a world. Wind may be null. */
	static FLSCompassReading Read(const ULSStorySubsystem& Story, const ULSMapSubsystem* Map, const UWindSubsystem* Wind,
		const FVector& From, const FVector& Facing, float ImpossibleRouteRange);

	/** Fills the direction fields of a reading from a target. */
	static void Aim(FLSCompassReading& Reading, const FVector& From, const FVector& Facing, const FVector& Target);

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	float CooldownLeft = 0.f;
};

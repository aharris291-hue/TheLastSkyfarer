// The Last Skyfarer: the Ancient Glider (GDD 2).

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GliderModel.h"
#include "GliderComponent.generated.h"

class ACharacter;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnGliderEvent);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnGliderLanded, bool, bRollLanding);

/**
 * Flies the owning character with the energy model in FGliderModel and adds wind from
 * UWindSubsystem. While gliding the character uses MOVE_Flying and this component sets its velocity.
 */
UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API UGliderComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGliderComponent();

	/** Owned from Chapter 3. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	bool bHasGlider = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	FGliderParams Params;

	/** Accessibility assist (GDD 2.4). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	bool bAssistMode = false;

	/** Minimum height above ground to allow deploying, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float MinDeployHeight = 150.f;

	/** Seconds of stagger after a roll landing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float RollLandingStagger = 0.4f;

	UPROPERTY(BlueprintAssignable, Category = "Glider")
	FOnGliderEvent OnDeployed;

	UPROPERTY(BlueprintAssignable, Category = "Glider")
	FOnGliderLanded OnLanded;

	UFUNCTION(BlueprintCallable, Category = "Glider")
	bool TryDeploy();

	UFUNCTION(BlueprintCallable, Category = "Glider")
	void Stow();

	UFUNCTION(BlueprintPure, Category = "Glider")
	bool IsGliding() const { return bGliding; }

	UFUNCTION(BlueprintPure, Category = "Glider")
	float GetAirspeed() const { return State.Speed; }

	UFUNCTION(BlueprintPure, Category = "Glider")
	const FGliderState& GetState() const { return State; }

	/** Stick input while gliding: X = turn, Y = pitch (+ dive). */
	void SetControlInput(float Turn, float Pitch) { Input.Turn = Turn; Input.Pitch = Pitch; }
	void SetAirBrake(bool bOn) { Input.bAirBrake = bOn; }

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<ACharacter> Character;

	FGliderState State;
	FGliderInput Input;
	bool bGliding = false;

	void Land(float ImpactSpeed);
	bool IsNearGround(float Distance, FHitResult& OutHit) const;
};

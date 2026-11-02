// The Last Skyfarer: Kieran, the player character (GDD 1 and 2).

#pragma once

#include "CoreMinimal.h"
#include "LastSkyfarerCharacter.h"
#include "GliderModel.h"
#include "LSPlayerCharacter.generated.h"

class UGliderComponent;
class UInputAction;
class UInputMappingContext;

/**
 * Third-person explorer built on the template character. Adds walk/run/sprint, coyote time and
 * jump buffering, glider deploy, a speed-driven camera and recovery to the last safe ledge.
 */
UCLASS(Blueprintable)
class LASTSKYFARER_API ALSPlayerCharacter : public ALastSkyfarerCharacter
{
	GENERATED_BODY()

public:
	ALSPlayerCharacter();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Glider")
	TObjectPtr<UGliderComponent> Glider;

	// Movement (cm/s). GDD 1: walk 1.8, run 4.5, sprint 6.5 m/s.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float WalkSpeed = 180.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float RunSpeed = 450.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float SprintSpeed = 650.f;

	/** Sprint ends after this many seconds... */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float SprintDuration = 4.f;

	/** ...and cannot restart for this long. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float SprintCooldown = 2.f;

	/** Jump apex height, cm (1.3 m). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float JumpHeight = 130.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float CoyoteTime = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Movement")
	float JumpBufferTime = 0.15f;

	// Camera (GDD 1).
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera")
	float CameraDistance = 320.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera")
	float CameraGlideDistance = 600.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera")
	float CameraShoulderOffset = 45.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera")
	float BaseFOV = 80.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Camera")
	float MaxGlideFOV = 95.f;

	// Recovery (GDD 2.5).
	/** Falling below this height returns Kieran to the last safe ledge, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recovery")
	float RecoveryZ = -20000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Recovery")
	float SafePointInterval = 2.f;

	/** Extra input actions; created with default keys at runtime if left empty. */
	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> SprintAction;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> WalkToggleAction;

	UPROPERTY(EditAnywhere, Category = "Input")
	TObjectPtr<UInputAction> AirBrakeAction;

	UFUNCTION(BlueprintCallable, Category = "Recovery")
	void RecoverToSafePoint();

	UFUNCTION(BlueprintPure, Category = "Recovery")
	FVector GetSafePoint() const { return SafePoints.SafePoint; }

	/** Samples the current position as safe if standing on stable ground (also called from Tick). */
	void SampleSafePoint(double Now, bool bForceStable = false);

	/** Checks the recovery height and recovers if below it. Returns true if it recovered. */
	bool CheckRecovery();

	virtual void DoMove(float Right, float Forward) override;
	virtual void DoJumpStart() override;
	virtual void DoJumpEnd() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void Landed(const FHitResult& Hit) override;
	virtual void NotifyControllerChanged() override;

protected:
	virtual void BeginPlay() override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void OnMovementModeChanged(EMovementMode PrevMovementMode, uint8 PreviousCustomMode = 0) override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UInputMappingContext> ExtraMappingContext;

	FSafePointTracker SafePoints;
	bool bWalkMode = false;
	bool bSprinting = false;
	double SprintStartTime = -100.0;
	double SprintEndTime = -100.0;
	double LeftGroundTime = -100.0;
	double JumpPressedTime = -100.0;
	bool bJumpedSinceGrounded = false;

	void EnsureExtraInput();
	void StartSprint();
	void StopSprint();
	void ToggleWalk();
	void AirBrakePressed();
	void AirBrakeReleased();
	void UpdateSpeed();
	void UpdateCamera(float DeltaSeconds);
	double Now() const;
};

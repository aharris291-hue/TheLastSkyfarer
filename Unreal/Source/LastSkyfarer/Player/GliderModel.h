// The Last Skyfarer: pure glider flight model (GDD 2.1). No engine state, so it can be unit tested.

#pragma once

#include "CoreMinimal.h"
#include "GliderModel.generated.h"

/** Tunables for the energy-based glider. All speeds in m/s, angles in degrees. */
USTRUCT(BlueprintType)
struct LASTSKYFARER_API FGliderParams
{
	GENERATED_BODY()

	/** Neutral glide speed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float TrimSpeed = 14.f;

	/** Sink rate at trim speed with no pitch input. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float TrimSinkRate = 1.6f;

	/** Speed cap in a dive. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float MaxDiveSpeed = 32.f;

	/** Below this the glider stalls and noses down. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float StallSpeed = 7.f;

	/** Stall ends once speed is back above this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float StallRecoverSpeed = 9.f;

	/** Share of kinetic energy turned into height when pulling up (the rest is lost). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider", meta = (ClampMin = "0.05", ClampMax = "1.0"))
	float PullUpEfficiency = 0.7f;

	/** Extra deceleration while the air brake is held. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float AirBrakeDecel = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float MaxDiveAngle = 45.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float MaxClimbAngle = 30.f;

	/** Nose-down angle while stalled. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float StallNoseDownAngle = 30.f;

	/** How fast the flight-path angle follows the stick. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float PitchRate = 90.f;

	/** Turn rate at trim speed; it falls as speed rises. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float TurnRateAtTrim = 60.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float MinTurnRate = 18.f;

	/** Touching ground below this folds the glider into a run; above it is a roll landing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float SafeLandingSpeed = 18.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Glider")
	float Gravity = 9.81f;
};

USTRUCT(BlueprintType)
struct LASTSKYFARER_API FGliderState
{
	GENERATED_BODY()

	/** Airspeed along the flight path, m/s. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Glider")
	float Speed = 14.f;

	/** Flight-path angle, degrees (negative = descending). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Glider")
	float PathAngle = 0.f;

	/** Heading, degrees. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Glider")
	float Yaw = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Glider")
	bool bStalled = false;
};

struct FGliderInput
{
	/** +1 = stick forward (dive), -1 = stick back (pull up). */
	float Pitch = 0.f;
	/** -1 left .. +1 right. */
	float Turn = 0.f;
	bool bAirBrake = false;
	/** Accessibility assist: holds altitude when there is no pitch input. */
	bool bAssist = false;
};

struct FGliderStepResult
{
	/** Displacement through the air in metres (X forward along heading at Yaw = 0, Z up). Wind is added by the caller. */
	FVector AirDisplacement = FVector::ZeroVector;
	float HeightDelta = 0.f;
};

struct LASTSKYFARER_API FGliderModel
{
	/** Neutral glide path angle (negative), from trim speed and sink rate. */
	static float TrimPathAngle(const FGliderParams& P);

	/** Linear drag constant (per second) chosen so trim flight is steady. */
	static float DragCoefficient(const FGliderParams& P);

	/** Starts a glide from the current velocity (m/s, world axes). */
	static FGliderState FromVelocity(const FVector& VelocityMS, const FGliderParams& P);

	/**
	 * Advances one step. Height uses the average of old and new speed, so without the assist
	 * the specific energy (g*h + v^2/2) can never rise, whatever the step size.
	 */
	static FGliderStepResult Step(FGliderState& S, const FGliderInput& In, const FGliderParams& P, float Dt);

	static float SpecificEnergy(float Speed, float HeightM, const FGliderParams& P)
	{
		return P.Gravity * HeightM + 0.5f * Speed * Speed;
	}

	static float TurnRate(float Speed, const FGliderParams& P);

	/** Touching ground faster than SafeLandingSpeed is a roll landing with a short stagger. */
	static bool IsRollLanding(float ImpactSpeed, const FGliderParams& P) { return ImpactSpeed > P.SafeLandingSpeed; }
};

/** Remembers the last stable ground position, sampled at a fixed interval (GDD 2.5). */
struct LASTSKYFARER_API FSafePointTracker
{
	float SampleInterval = 2.f;
	double LastSampleTime = -1.0e9;
	FVector SafePoint = FVector::ZeroVector;
	bool bHasSafePoint = false;

	void Update(double Now, const FVector& Location, bool bOnStableGround)
	{
		if (bOnStableGround && (!bHasSafePoint || Now - LastSampleTime >= SampleInterval))
		{
			SafePoint = Location;
			LastSampleTime = Now;
			bHasSafePoint = true;
		}
	}

	void Reset()
	{
		*this = FSafePointTracker();
	}
};

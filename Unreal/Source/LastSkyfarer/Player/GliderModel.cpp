// The Last Skyfarer: pure glider flight model (GDD 2.1).

#include "GliderModel.h"

float FGliderModel::TrimPathAngle(const FGliderParams& P)
{
	const float SinGamma = FMath::Clamp(P.TrimSinkRate / FMath::Max(P.TrimSpeed, 0.1f), 0.f, 0.99f);
	return -FMath::RadiansToDegrees(FMath::Asin(SinGamma));
}

float FGliderModel::DragCoefficient(const FGliderParams& P)
{
	// Linear drag, chosen so trim flight is steady: drag deceleration equals the gravity component along the path.
	const float SinGamma = FMath::Clamp(P.TrimSinkRate / FMath::Max(P.TrimSpeed, 0.1f), 0.f, 0.99f);
	return P.Gravity * SinGamma / FMath::Max(P.TrimSpeed, 0.1f);
}

FGliderState FGliderModel::FromVelocity(const FVector& VelocityMS, const FGliderParams& P)
{
	FGliderState S;
	const FVector Horizontal(VelocityMS.X, VelocityMS.Y, 0.f);
	S.Yaw = Horizontal.IsNearlyZero() ? 0.f : FMath::RadiansToDegrees(FMath::Atan2(Horizontal.Y, Horizontal.X));
	// Deploying keeps forward momentum but never starts slower than a gentle stall recovery.
	S.Speed = FMath::Clamp(Horizontal.Size(), P.StallRecoverSpeed, P.MaxDiveSpeed);
	S.PathAngle = TrimPathAngle(P);
	return S;
}

float FGliderModel::TurnRate(float Speed, const FGliderParams& P)
{
	const float Scaled = P.TurnRateAtTrim * P.TrimSpeed / FMath::Max(Speed, 1.f);
	return FMath::Clamp(Scaled, P.MinTurnRate, P.TurnRateAtTrim * 1.5f);
}

FGliderStepResult FGliderModel::Step(FGliderState& S, const FGliderInput& In, const FGliderParams& P, float Dt)
{
	FGliderStepResult Out;
	if (Dt <= 0.f)
	{
		return Out;
	}

	const float Pitch = FMath::Clamp(In.Pitch, -1.f, 1.f);
	const bool bAssistHold = In.bAssist && FMath::Abs(Pitch) < 0.1f;
	const float Trim = TrimPathAngle(P);

	// Stall handling.
	if (S.Speed < P.StallSpeed)
	{
		S.bStalled = true;
	}
	else if (S.bStalled && S.Speed >= P.StallRecoverSpeed)
	{
		S.bStalled = false;
	}

	float TargetAngle;
	if (S.bStalled)
	{
		TargetAngle = -P.StallNoseDownAngle;
	}
	else if (bAssistHold)
	{
		TargetAngle = 0.f;
	}
	else if (Pitch >= 0.f)
	{
		TargetAngle = FMath::Lerp(Trim, -P.MaxDiveAngle, Pitch);
	}
	else
	{
		TargetAngle = FMath::Lerp(Trim, P.MaxClimbAngle, -Pitch);
	}
	S.PathAngle = FMath::FInterpConstantTo(S.PathAngle, TargetAngle, Dt, P.PitchRate);

	const float SinG = FMath::Sin(FMath::DegreesToRadians(S.PathAngle));
	const float CosG = FMath::Cos(FMath::DegreesToRadians(S.PathAngle));

	// Speed change along the path. Diving converts height to speed one to one; climbing pays
	// 1/PullUpEfficiency in speed per unit of height, so only ~70% of kinetic energy comes back.
	float Accel = -DragCoefficient(P) * S.Speed;
	Accel += (SinG < 0.f) ? (-P.Gravity * SinG) : (-P.Gravity * SinG / FMath::Max(P.PullUpEfficiency, 0.05f));
	if (In.bAirBrake)
	{
		Accel -= P.AirBrakeDecel;
	}
	if (bAssistHold && !In.bAirBrake)
	{
		// Assist cancels losses and eases back to trim (accessibility; not energy-conserving by design).
		Accel = (P.TrimSpeed - S.Speed) * 0.8f;
	}

	const float OldSpeed = S.Speed;
	const float NewSpeed = FMath::Clamp(OldSpeed + Accel * Dt, 0.5f, P.MaxDiveSpeed);
	S.Speed = NewSpeed;

	const float AvgSpeed = 0.5f * (OldSpeed + NewSpeed);
	S.Yaw = FRotator::NormalizeAxis(S.Yaw + FMath::Clamp(In.Turn, -1.f, 1.f) * TurnRate(AvgSpeed, P) * Dt);

	const float YawRad = FMath::DegreesToRadians(S.Yaw);
	const float Horizontal = AvgSpeed * CosG * Dt;
	Out.HeightDelta = AvgSpeed * SinG * Dt;
	Out.AirDisplacement = FVector(Horizontal * FMath::Cos(YawRad), Horizontal * FMath::Sin(YawRad), Out.HeightDelta);
	return Out;
}

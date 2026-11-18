// The Last Skyfarer: automation tests for the glider, recovery, wind and Piko (Phase 3).

#include "Misc/AutomationTest.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GliderModel.h"
#include "LSPlayerCharacter.h"
#include "PikoCompanion.h"
#include "WindVolume.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace LSSystemsTest
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter;

	/** A bare game world for spawning actors in tests. */
	struct FScopedWorld
	{
		UWorld* World = nullptr;

		FScopedWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("LSSystemsTestWorld"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
		}

		~FScopedWorld()
		{
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}
	};

	/** Flies the pure model for Seconds with a fixed input and tracks energy. Returns false if energy ever rose. */
	bool Fly(FGliderState& S, float& Height, const FGliderInput& In, const FGliderParams& P, float Seconds, float Dt, float& MaxRise, float* MaxHeight = nullptr)
	{
		bool bNeverRose = true;
		for (float T = 0.f; T < Seconds; T += Dt)
		{
			const float Before = FGliderModel::SpecificEnergy(S.Speed, Height, P);
			Height += FGliderModel::Step(S, In, P, Dt).HeightDelta;
			const float After = FGliderModel::SpecificEnergy(S.Speed, Height, P);
			MaxRise = FMath::Max(MaxRise, After - Before);
			if (MaxHeight) { *MaxHeight = FMath::Max(*MaxHeight, Height); }
			if (After > Before + 1.0e-3f)
			{
				bNeverRose = false;
			}
		}
		return bNeverRose;
	}

	AWindVolume* SpawnStraightVolume(UWorld* World, EWindVolumeType Type, const FVector& Start, const FVector& End, bool bHidden)
	{
		FActorSpawnParameters SpawnParams;
		SpawnParams.bDeferConstruction = true;
		AWindVolume* V = World->SpawnActor<AWindVolume>(AWindVolume::StaticClass(), FTransform(Start), SpawnParams);
		V->WindType = Type;
		V->bStartsHidden = bHidden;
		V->Radius = 500.f;
		V->Strength = Type == EWindVolumeType::Updraft ? 6.f : 14.f;
		V->Spline->ClearSplinePoints(false);
		V->Spline->AddSplinePoint(Start, ESplineCoordinateSpace::World, false);
		V->Spline->AddSplinePoint(End, ESplineCoordinateSpace::World, true);
		V->FinishSpawning(FTransform(Start));
		World->GetSubsystem<UWindSubsystem>()->Register(V);
		return V;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSGliderTrimTest, "LastSkyfarer.Systems.Glider.TrimFlight", LSSystemsTest::Flags)
bool FLSGliderTrimTest::RunTest(const FString& Parameters)
{
	const FGliderParams P;
	FGliderState S;
	S.Speed = P.TrimSpeed;
	S.PathAngle = FGliderModel::TrimPathAngle(P);
	float Height = 0.f;
	for (int32 i = 0; i < 600; ++i)
	{
		Height += FGliderModel::Step(S, FGliderInput(), P, 1.f / 60.f).HeightDelta;
	}
	TestNearlyEqual(TEXT("Trim speed holds at 14 m/s"), S.Speed, P.TrimSpeed, 0.05f);
	TestNearlyEqual(TEXT("Sink rate is 1.6 m/s at trim"), -Height / 10.f, P.TrimSinkRate, 0.05f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSGliderEnergyTest, "LastSkyfarer.Systems.Glider.NoNetEnergyGain", LSSystemsTest::Flags)
bool FLSGliderEnergyTest::RunTest(const FString& Parameters)
{
	const FGliderParams P;
	for (const float Dt : { 1.f / 120.f, 1.f / 30.f, 0.1f })
	{
		FGliderState S;
		S.Speed = P.TrimSpeed;
		S.PathAngle = FGliderModel::TrimPathAngle(P);
		float Height = 300.f;
		const float Start = FGliderModel::SpecificEnergy(S.Speed, Height, P);
		float MaxRise = -1.f;

		FGliderInput Dive; Dive.Pitch = 1.f;
		FGliderInput Climb; Climb.Pitch = -1.f;
		bool bOk = LSSystemsTest::Fly(S, Height, Dive, P, 6.f, Dt, MaxRise);
		const float TopSpeed = S.Speed;
		const float HeightAfterDive = Height;
		float PeakHeight = Height;
		bOk &= LSSystemsTest::Fly(S, Height, Climb, P, 8.f, Dt, MaxRise, &PeakHeight);
		const float End = FGliderModel::SpecificEnergy(S.Speed, Height, P);

		const FString Tag = FString::Printf(TEXT("dt=%.4f"), Dt);
		TestTrue(Tag + TEXT(": energy never rises in any step"), bOk);
		TestTrue(Tag + TEXT(": no net energy gain over dive and pull-up"), End <= Start + 1.0e-3f);
		TestTrue(Tag + TEXT(": dive is capped at 32 m/s"), TopSpeed <= P.MaxDiveSpeed + 1.0e-3f);
		TestTrue(Tag + TEXT(": dive reaches at least 25 m/s"), TopSpeed >= 25.f);

		const float KineticAboveTrim = 0.5f * (TopSpeed * TopSpeed - P.TrimSpeed * P.TrimSpeed) / P.Gravity;
		const float Regained = PeakHeight - HeightAfterDive;
		TestTrue(Tag + TEXT(": pull-up regains no more than 70% of dive energy"), Regained <= P.PullUpEfficiency * KineticAboveTrim + 0.5f);
		TestTrue(Tag + TEXT(": pull-up regains a useful share of height"), Regained >= 0.3f * KineticAboveTrim);
		AddInfo(FString::Printf(TEXT("%s: top %.1f m/s, regained %.1f m of %.1f m possible, max step rise %.6f"), *Tag, TopSpeed, Regained, KineticAboveTrim, MaxRise));
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSGliderPullUpTest, "LastSkyfarer.Systems.Glider.PullUpReturns70Percent", LSSystemsTest::Flags)
bool FLSGliderPullUpTest::RunTest(const FString& Parameters)
{
	// With drag almost removed, a steady climb turns 70% of the lost kinetic energy into height.
	FGliderParams P;
	P.TrimSinkRate = 0.001f;
	FGliderState S;
	S.Speed = 32.f;
	S.PathAngle = P.MaxClimbAngle;
	FGliderInput Climb; Climb.Pitch = -1.f;
	float Height = 0.f;
	while (S.Speed > 14.f)
	{
		Height += FGliderModel::Step(S, Climb, P, 1.f / 240.f).HeightDelta;
	}
	const float KineticLost = 0.5f * (32.f * 32.f - S.Speed * S.Speed) / P.Gravity;
	TestNearlyEqual(TEXT("Height gained is 70% of kinetic energy lost"), Height / KineticLost, 0.7f, 0.02f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSGliderStallTest, "LastSkyfarer.Systems.Glider.StallAndRecover", LSSystemsTest::Flags)
bool FLSGliderStallTest::RunTest(const FString& Parameters)
{
	const FGliderParams P;
	FGliderState S;
	S.Speed = 7.5f;
	S.PathAngle = 0.f;
	FGliderModel::Step(S, FGliderInput(), P, 1.f / 60.f);
	TestFalse(TEXT("7.5 m/s is not a stall"), S.bStalled);

	S = FGliderState();
	S.Speed = 6.5f;
	FGliderInput PullUp; PullUp.Pitch = -1.f;
	FGliderModel::Step(S, PullUp, P, 1.f / 60.f);
	TestTrue(TEXT("Below 7 m/s the glider stalls"), S.bStalled);

	bool bRecovered = false;
	float MinSpeed = S.Speed;
	for (int32 i = 0; i < 600 && !bRecovered; ++i)
	{
		FGliderModel::Step(S, PullUp, P, 1.f / 60.f); // even holding pull-up, the stall noses down
		MinSpeed = FMath::Min(MinSpeed, S.Speed);
		bRecovered = !S.bStalled;
	}
	TestTrue(TEXT("Stall recovers on its own"), bRecovered);
	TestTrue(TEXT("Recovered above 9 m/s"), S.Speed >= P.StallRecoverSpeed);
	TestTrue(TEXT("Speed never collapsed"), MinSpeed > 1.f);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSGliderLandingTest, "LastSkyfarer.Systems.Glider.LandingThreshold", LSSystemsTest::Flags)
bool FLSGliderLandingTest::RunTest(const FString& Parameters)
{
	const FGliderParams P;
	TestFalse(TEXT("17.9 m/s folds into a run"), FGliderModel::IsRollLanding(17.9f, P));
	TestFalse(TEXT("18 m/s folds into a run"), FGliderModel::IsRollLanding(18.f, P));
	TestTrue(TEXT("18.1 m/s is a roll landing"), FGliderModel::IsRollLanding(18.1f, P));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSRecoveryTest, "LastSkyfarer.Systems.Recovery.ReturnsToLastSafePoint", LSSystemsTest::Flags)
bool FLSRecoveryTest::RunTest(const FString& Parameters)
{
	// Tracker rules.
	FSafePointTracker Tracker;
	Tracker.Update(0.0, FVector(0, 0, 100), true);
	Tracker.Update(1.0, FVector(500, 0, 100), true);      // too soon: interval is 2 s
	TestEqual(TEXT("Samples no more often than every 2 s"), Tracker.SafePoint, FVector(0, 0, 100));
	Tracker.Update(2.5, FVector(800, 0, 100), true);
	Tracker.Update(5.0, FVector(1500, 0, -3000), false);  // in the air: not safe
	TestEqual(TEXT("Only stable ground is sampled"), Tracker.SafePoint, FVector(800, 0, 100));

	// The character falls below the cloud sea and comes back.
	LSSystemsTest::FScopedWorld Scoped;
	ALSPlayerCharacter* Kieran = Scoped.World->SpawnActor<ALSPlayerCharacter>(FVector(1000, 2000, 300), FRotator::ZeroRotator);
	if (!TestNotNull(TEXT("Spawned the player character"), Kieran))
	{
		return false;
	}
	Kieran->SampleSafePoint(10.0, true);
	const FVector Safe = Kieran->GetActorLocation();
	TestFalse(TEXT("No recovery while above the cloud sea"), Kieran->CheckRecovery());
	Kieran->SetActorLocation(FVector(30000, 0, Kieran->RecoveryZ - 500.f), false, nullptr, ETeleportType::TeleportPhysics);
	TestTrue(TEXT("Recovery triggers below the cloud sea"), Kieran->CheckRecovery());
	TestTrue(TEXT("Returned to the last safe point"), Kieran->GetActorLocation().Equals(Safe, 1.f));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSWindTest, "LastSkyfarer.Systems.Wind.CurrentsAndUpdrafts", LSSystemsTest::Flags)
bool FLSWindTest::RunTest(const FString& Parameters)
{
	LSSystemsTest::FScopedWorld Scoped;
	UWindSubsystem* Wind = Scoped.World->GetSubsystem<UWindSubsystem>();
	LSSystemsTest::SpawnStraightVolume(Scoped.World, EWindVolumeType::Current, FVector(0, 0, 1000), FVector(10000, 0, 1000), false);
	LSSystemsTest::SpawnStraightVolume(Scoped.World, EWindVolumeType::Updraft, FVector(0, 5000, 0), FVector(0, 5000, 3000), false);

	const FWindSample InCurrent = Wind->SampleWind(FVector(5000, 0, 1000));
	TestTrue(TEXT("Inside the current"), InCurrent.bInside);
	TestNearlyEqual(TEXT("Current pushes along its spline at 14 m/s"), InCurrent.Velocity.X, 1400.0, 1.0);
	TestTrue(TEXT("Current holds altitude"), InCurrent.bHoldAltitude);

	const FWindSample InUpdraft = Wind->SampleWind(FVector(0, 5000, 1500));
	TestTrue(TEXT("Updraft lifts"), InUpdraft.Velocity.Z > 500.f);

	const FWindSample Outside = Wind->SampleWind(FVector(5000, 0, 3000));
	TestFalse(TEXT("No wind outside the radius"), Outside.bInside);

	const FWindSample PastEnd = Wind->SampleWind(FVector(11000, 0, 1000));
	TestFalse(TEXT("No wind past the end of the current"), PastEnd.bInside);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSHiddenCurrentTest, "LastSkyfarer.Systems.Wind.HiddenUntilPikoSenses", LSSystemsTest::Flags)
bool FLSHiddenCurrentTest::RunTest(const FString& Parameters)
{
	LSSystemsTest::FScopedWorld Scoped;
	UWindSubsystem* Wind = Scoped.World->GetSubsystem<UWindSubsystem>();
	AWindVolume* Hidden = LSSystemsTest::SpawnStraightVolume(Scoped.World, EWindVolumeType::Current, FVector(0, 0, 2000), FVector(8000, 0, 2000), true);

	TestFalse(TEXT("Hidden current starts unrevealed"), Hidden->IsRevealed());
	TestFalse(TEXT("Hidden current is invisible"), Hidden->Visual->IsVisible());
	TestFalse(TEXT("Hidden current does not push"), Wind->SampleWind(FVector(4000, 0, 2000)).bInside);

	APikoCompanion* Piko = Scoped.World->SpawnActor<APikoCompanion>(FVector(4000, 10000, 2000), FRotator::ZeroRotator);
	if (!TestNotNull(TEXT("Spawned Piko"), Piko))
	{
		return false;
	}
	TestEqual(TEXT("Piko at 100 m senses nothing"), Piko->Sense(), 0);
	TestFalse(TEXT("Still hidden at 100 m"), Hidden->IsRevealed());

	Piko->SetActorLocation(FVector(4000, 4500, 2000)); // 45 m away: glows but out of range
	TestEqual(TEXT("Piko at 45 m senses nothing"), Piko->Sense(), 0);
	TestTrue(TEXT("Markings glow as a hidden current gets close"), Piko->MarkingGlow > 0.f);

	Piko->SetActorLocation(FVector(4000, 3500, 2000)); // 35 m away
	TestEqual(TEXT("Piko within 40 m reveals the current"), Piko->Sense(), 1);
	TestTrue(TEXT("Revealed"), Hidden->IsRevealed());
	TestTrue(TEXT("Now visible"), Hidden->Visual->IsVisible());
	TestTrue(TEXT("Now pushes the glider"), Wind->SampleWind(FVector(4000, 0, 2000)).bInside);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS

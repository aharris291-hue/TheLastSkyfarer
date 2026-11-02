// The Last Skyfarer: traversal tests. Ledge detection uses real collision traces against boxes;
// the mantle/hang/climb decision is checked for each case. (Character movement itself is checked
// end to end in a game run of L_SystemsTest with -LSTraversalCheck, because a bare automation world
// does not simulate character movement.)

#include "Misc/AutomationTest.h"

#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"
#include "LSPlayerCharacter.h"
#include "LSTraversalComponent.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace LSTraversalTest
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter;

	struct FScene
	{
		UWorld* World = nullptr;
		ALSPlayerCharacter* Kieran = nullptr;

		FScene()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("LSTraversalTestWorld"));
			FWorldContext& Context = GEngine->CreateNewWorldContext(EWorldType::Game);
			Context.SetCurrentWorld(World);
			World->InitializeActorsForPlay(FURL());
			World->GetWorldSettings()->NotifyBeginPlay();
		}

		~FScene()
		{
			GEngine->DestroyWorldContext(World);
			World->DestroyWorld(false);
		}

		/** Box with its base at BaseZ and its front face at X = 200. */
		AStaticMeshActor* Box(float Height, bool bClimbable = false, float BaseZ = 0.f, float Depth = 200.f)
		{
			const FVector Size(Depth, 800.f, Height);
			AStaticMeshActor* A = World->SpawnActor<AStaticMeshActor>(FVector(200.f + Depth / 2.f, 0.f, BaseZ + Height / 2.f), FRotator::ZeroRotator);
			UStaticMeshComponent* C = A->GetStaticMeshComponent();
			C->SetMobility(EComponentMobility::Movable);
			C->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
			C->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
			A->SetActorScale3D(Size / 100.f);
			if (bClimbable)
			{
				A->Tags.Add(TEXT("Climbable"));
			}
			return A;
		}

		/** Kieran facing +X with his feet at FeetZ, capsule front 10 cm from the box face. */
		ULSTraversalComponent* Place(float FeetZ)
		{
			if (!Kieran)
			{
				Kieran = World->SpawnActor<ALSPlayerCharacter>(FVector(-1000.f, 0.f, 2000.f), FRotator::ZeroRotator);
			}
			const UCapsuleComponent* Capsule = Kieran->GetCapsuleComponent();
			Kieran->SetActorLocation(FVector(200.f - Capsule->GetScaledCapsuleRadius() - 10.f, 0.f, FeetZ + Capsule->GetScaledCapsuleHalfHeight()));
			return Kieran->Traversal;
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSMantleHeightsTest, "LastSkyfarer.Systems.Traversal.MantleHeights", LSTraversalTest::Flags)
bool FLSMantleHeightsTest::RunTest(const FString& Parameters)
{
	// GDD: mantle automatically on obstacles 0.5 to 1.8 m high while moving into them.
	struct FCase { float Height; ETraversalState Expected; };
	for (const FCase Case : { FCase{ 40.f, ETraversalState::None }, FCase{ 60.f, ETraversalState::Mantling }, FCase{ 120.f, ETraversalState::Mantling },
		FCase{ 175.f, ETraversalState::Mantling }, FCase{ 200.f, ETraversalState::None }, FCase{ 300.f, ETraversalState::None } })
	{
		LSTraversalTest::FScene Scene;
		Scene.Box(Case.Height);
		ULSTraversalComponent* T = Scene.Place(0.f);
		FLSLedge Ledge;
		const FString Tag = FString::Printf(TEXT("%.0f cm box"), Case.Height);
		TestTrue(Tag + TEXT(": wall found"), T->FindLedge(FVector::ForwardVector, Ledge));
		if (Case.Height >= T->MinMantleHeight && Case.Height <= T->MaxHangReach)
		{
			TestTrue(Tag + TEXT(": top found"), Ledge.bHasTop);
			TestNearlyEqual(Tag + TEXT(": measured height"), Ledge.Height, Case.Height, 3.f);
		}
		TestEqual(Tag + TEXT(": walking into it"), T->Classify(Ledge, false, true, 0.f), Case.Expected);
		TestEqual(Tag + TEXT(": standing still next to it does nothing"), T->Classify(Ledge, false, false, 0.f), ETraversalState::None);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSLedgeHangTest, "LastSkyfarer.Systems.Traversal.LedgeHangReach", LSTraversalTest::Flags)
bool FLSLedgeHangTest::RunTest(const FString& Parameters)
{
	LSTraversalTest::FScene Scene;
	const float Top = 600.f;
	Scene.Box(Top);
	FLSLedge Ledge;

	ULSTraversalComponent* T = Scene.Place(Top - 200.f);
	T->FindLedge(FVector::ForwardVector, Ledge);
	TestEqual(TEXT("Ledge 2.0 m above the feet while falling: hang"), T->Classify(Ledge, true, false, -300.f), ETraversalState::Hanging);
	TestEqual(TEXT("Same ledge while still rising: no grab yet"), T->Classify(Ledge, true, false, 200.f), ETraversalState::None);

	T = Scene.Place(Top - 150.f);
	T->FindLedge(FVector::ForwardVector, Ledge);
	TestEqual(TEXT("Ledge 1.5 m above the feet while falling: mantle"), T->Classify(Ledge, true, false, -300.f), ETraversalState::Mantling);

	T = Scene.Place(Top - 260.f);
	T->FindLedge(FVector::ForwardVector, Ledge);
	TestEqual(TEXT("Ledge 2.6 m above the feet: out of reach"), T->Classify(Ledge, true, false, -300.f), ETraversalState::None);
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSClimbTagTest, "LastSkyfarer.Systems.Traversal.ClimbOnlyTaggedWalls", LSTraversalTest::Flags)
bool FLSClimbTagTest::RunTest(const FString& Parameters)
{
	{
		LSTraversalTest::FScene Scene;
		Scene.Box(600.f, /*bClimbable*/ true);
		ULSTraversalComponent* T = Scene.Place(0.f);
		FLSLedge Ledge;
		T->FindLedge(FVector::ForwardVector, Ledge);
		TestTrue(TEXT("Tagged wall is recognised as climbable"), Ledge.bClimbable);
		TestEqual(TEXT("Walking into a tagged wall: climb"), T->Classify(Ledge, false, true, 0.f), ETraversalState::Climbing);
		TestEqual(TEXT("Not pushing into it: nothing"), T->Classify(Ledge, false, false, 0.f), ETraversalState::None);
	}
	{
		LSTraversalTest::FScene Scene;
		Scene.Box(600.f, /*bClimbable*/ false);
		ULSTraversalComponent* T = Scene.Place(0.f);
		FLSLedge Ledge;
		T->FindLedge(FVector::ForwardVector, Ledge);
		TestFalse(TEXT("Untagged wall is not climbable"), Ledge.bClimbable);
		TestEqual(TEXT("Walking into an untagged wall: nothing"), T->Classify(Ledge, false, true, 0.f), ETraversalState::None);
	}
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNoRoomTest, "LastSkyfarer.Systems.Traversal.NoMantleWithoutRoom", LSTraversalTest::Flags)
bool FLSNoRoomTest::RunTest(const FString& Parameters)
{
	LSTraversalTest::FScene Scene;
	Scene.Box(120.f);
	// A slab 1 m above the top leaves no room to stand.
	Scene.Box(100.f, false, 220.f, 400.f);
	ULSTraversalComponent* T = Scene.Place(0.f);
	FLSLedge Ledge;
	T->FindLedge(FVector::ForwardVector, Ledge);
	TestFalse(TEXT("No room on top"), Ledge.bHasTop);
	TestEqual(TEXT("No mantle into a gap too low to stand in"), T->Classify(Ledge, false, true, 0.f), ETraversalState::None);
	return true;
}

#endif // WITH_DEV_AUTOMATION_TESTS

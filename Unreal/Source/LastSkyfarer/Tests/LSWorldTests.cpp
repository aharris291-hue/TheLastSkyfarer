// The Last Skyfarer: automation tests for interaction and restoration (Phase 3).
// Run: -ExecCmds="Automation RunTests LastSkyfarer.World; Quit"

#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "LSInteractableComponent.h"
#include "LSInteractionSubsystem.h"
#include "LSRestorationTypes.h"
#include "LSStorySubsystem.h"
#include "LSStoryVolumes.h"

namespace LSWorldTest
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter;

	ULSStorySubsystem* MakeStory(FAutomationTestBase& Test)
	{
		FLSNarrativeDatabase Db;
		TArray<FString> Errors;
		Db.LoadFromDirectory(FLSNarrativeDatabase::DefaultDataDir(), Errors);
		for (const FString& E : Errors) Test.AddError(E);
		UGameInstance* GI = NewObject<UGameInstance>(GetTransientPackage());
		ULSStorySubsystem* Story = NewObject<ULSStorySubsystem>(GI);
		Story->InitWithDatabase(Db);
		return Story;
	}

	FLSStoryAction Action(ELSActionType Type, const FString& Arg)
	{
		FLSStoryAction A;
		A.Type = Type;
		A.Arg = Arg;
		return A;
	}

	/** A bare game world for spawning actors (BeginPlay is not dispatched). */
	struct FScopedWorld
	{
		UWorld* World = nullptr;
		FScopedWorld()
		{
			World = UWorld::CreateWorld(EWorldType::Game, false, TEXT("LSWorldTestWorld"));
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

	void FinishDialogue(ULSStorySubsystem* Story)
	{
		for (int32 Guard = 0; Story->IsInDialogue() && Guard < 1000; ++Guard) Story->AdvanceDialogue();
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSInteractionRulesTest, "LastSkyfarer.World.Interaction.RulesAndDialogue", LSWorldTest::Flags)
bool FLSInteractionRulesTest::RunTest(const FString& Parameters)
{
	using namespace LSWorldTest;
	ULSStorySubsystem* Story = MakeStory(*this);
	ULSInteractableComponent* I = NewObject<ULSInteractableComponent>(GetTransientPackage());

	FLSInteractionRule First;
	First.If = { TEXT("!test_met") };
	First.Conversation = TEXT("maren_intro");
	First.Do = { Action(ELSActionType::SetFlag, TEXT("test_met")) };
	FLSInteractionRule Repeat;
	Repeat.bRepeat = true;
	Repeat.Do = { Action(ELSActionType::SetFlag, TEXT("test_repeat")) };
	I->Rules = { First, Repeat };

	TestEqual(TEXT("first rule picked"), ULSInteractableComponent::PickRuleIndex(I->Rules, *Story), 0);
	TestTrue(TEXT("new content marker"), I->HasNewContentFor(*Story));
	TestTrue(TEXT("interacts"), I->InteractWith(*Story, nullptr));
	TestTrue(TEXT("conversation running"), Story->IsInDialogue());
	TestFalse(TEXT("actions wait for the conversation"), Story->HasFlag(TEXT("test_met")));
	TestFalse(TEXT("no second interaction during dialogue"), I->InteractWith(*Story, nullptr));
	FinishDialogue(Story);
	TestTrue(TEXT("actions ran after the conversation"), Story->HasFlag(TEXT("test_met")));

	TestEqual(TEXT("repeat rule picked"), ULSInteractableComponent::PickRuleIndex(I->Rules, *Story), 1);
	TestFalse(TEXT("no marker for a repeat"), I->HasNewContentFor(*Story));
	TestTrue(TEXT("repeat interacts"), I->InteractWith(*Story, nullptr));
	TestTrue(TEXT("repeat actions run at once"), Story->HasFlag(TEXT("test_repeat")));

	I->AvailableIf = { TEXT("never_set") };
	TestFalse(TEXT("AvailableIf hides it"), I->CanInteractWith(*Story));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSInteractionFindBestTest, "LastSkyfarer.World.Interaction.FindBest", LSWorldTest::Flags)
bool FLSInteractionFindBestTest::RunTest(const FString& Parameters)
{
	using namespace LSWorldTest;
	ULSStorySubsystem* Story = MakeStory(*this);
	ULSInteractionSubsystem* Registry = NewObject<ULSInteractionSubsystem>(GetTransientPackage());

	auto Make = [&](const FVector& At, float Radius)
	{
		ULSInteractableComponent* I = NewObject<ULSInteractableComponent>(GetTransientPackage());
		I->Rules = { FLSInteractionRule() };
		I->Radius = Radius;
		I->SetWorldLocation(At);
		Registry->Register(I);
		return I;
	};
	ULSInteractableComponent* Front = Make(FVector(150, 0, 0), 200);
	ULSInteractableComponent* Behind = Make(FVector(-140, 0, 0), 200);
	Make(FVector(1000, 0, 0), 200);	// out of range

	TestTrue(TEXT("front beats behind at similar distance"), Registry->FindBest(FVector::ZeroVector, FVector::ForwardVector, *Story) == Front);
	TestTrue(TEXT("facing the other way picks the other one"), Registry->FindBest(FVector::ZeroVector, -FVector::ForwardVector, *Story) == Behind);
	TestTrue(TEXT("nothing in range"), Registry->FindBest(FVector(5000, 0, 0), FVector::ForwardVector, *Story) == nullptr);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSJournalPickupTest, "LastSkyfarer.World.Interaction.JournalPickup", LSWorldTest::Flags)
bool FLSJournalPickupTest::RunTest(const FString& Parameters)
{
	using namespace LSWorldTest;
	ULSStorySubsystem* Story = MakeStory(*this);

	FName EntryId;
	for (const TPair<FName, FLSJournalDef>& J : Story->GetDatabase().Journal)
	{
		if (J.Value.Collectible == TEXT("elias_notes")) { EntryId = J.Key; break; }
	}
	if (!TestFalse(TEXT("an Elias note exists"), EntryId.IsNone())) return false;

	FScopedWorld Scoped;
	ALSJournalPickup* Pickup = Scoped.World->SpawnActor<ALSJournalPickup>(FVector::ZeroVector, FRotator::ZeroRotator);
	if (!TestNotNull(TEXT("spawned"), Pickup)) return false;
	Pickup->JournalId = EntryId;
	Pickup->ConfigureRules();

	Story->StartQuest(TEXT("elias_was_here"));
	TestTrue(TEXT("picks up"), Pickup->Interactable->InteractWith(*Story, nullptr));
	TestTrue(TEXT("journal entry added"), Story->HasJournal(EntryId));
	TestTrue(TEXT("collected flag"), Story->HasFlag(Pickup->CollectedFlag()));
	TestTrue(TEXT("collectible advanced the quest"), Story->GetObjectiveProgress(TEXT("elias_was_here"), TEXT("notes")) == 1);
	TestFalse(TEXT("cannot pick up twice"), Pickup->Interactable->CanInteractWith(*Story));
	for (const FString& P : Story->Problems) AddError(P);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSRestorationStagesTest, "LastSkyfarer.World.Restoration.Stages", LSWorldTest::Flags)
bool FLSRestorationStagesTest::RunTest(const FString& Parameters)
{
	using namespace LSWorldTest;
	ULSStorySubsystem* Story = MakeStory(*this);
	const FName Id = TEXT("test");

	TMap<ELSRestorationStage, FLSStoryActionList> StageActions;
	StageActions.FindOrAdd(ELSRestorationStage::Investigated).Actions = { Action(ELSActionType::SetFlag, TEXT("ran_investigated")) };
	StageActions.FindOrAdd(ELSRestorationStage::Advanced).Actions = { Action(ELSActionType::SetFlag, TEXT("ran_advanced")) };

	TestTrue(TEXT("flag name"), ULSRestorationLibrary::StageFlag(Id, ELSRestorationStage::Restored) == FName(TEXT("beacon_test_restored")));
	TestTrue(TEXT("starts unknown"), ULSRestorationLibrary::GetStage(*Story, Id) == ELSRestorationStage::Unknown);

	TestTrue(TEXT("jumps to Restored"), ULSRestorationLibrary::AdvanceTo(*Story, Id, ELSRestorationStage::Restored, &StageActions));
	TestTrue(TEXT("now Restored"), ULSRestorationLibrary::GetStage(*Story, Id) == ELSRestorationStage::Restored);
	TestTrue(TEXT("passed stages flagged"), Story->HasFlag(TEXT("beacon_test_discovered")) && Story->HasFlag(TEXT("beacon_test_investigated")));
	TestTrue(TEXT("passed stage actions ran"), Story->HasFlag(TEXT("ran_investigated")));
	TestFalse(TEXT("never backwards"), ULSRestorationLibrary::AdvanceTo(*Story, Id, ELSRestorationStage::Discovered, &StageActions));
	TestFalse(TEXT("later actions not yet"), Story->HasFlag(TEXT("ran_advanced")));

	Story->SetFlag(TEXT("ran_investigated"), false);
	TestTrue(TEXT("to Advanced"), ULSRestorationLibrary::AdvanceTo(*Story, Id, ELSRestorationStage::Advanced, &StageActions));
	TestFalse(TEXT("earlier actions not rerun"), Story->HasFlag(TEXT("ran_investigated")));
	TestTrue(TEXT("final actions ran"), Story->HasFlag(TEXT("ran_advanced")));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSRingPuzzleTest, "LastSkyfarer.World.Restoration.RingPuzzle", LSWorldTest::Flags)
bool FLSRingPuzzleTest::RunTest(const FString& Parameters)
{
	TArray<FLSRingDef> Rings;
	for (int32 i = 0; i < 3; ++i)
	{
		FLSRingDef R;
		R.NumGlyphs = 8;
		R.Start = i;
		R.Target = 5;
		Rings.Add(R);
	}
	FLSRingPuzzle P;
	P.Reset(Rings);
	TestFalse(TEXT("unsolved at start"), P.IsSolved());
	TestTrue(TEXT("ring 0 forward"), P.Rotate(0, 5));
	TestTrue(TEXT("ring 0 aligned"), P.IsRingAligned(0));
	TestTrue(TEXT("ring 1 backwards wraps"), P.Rotate(1, -4));	// 1 - 4 = -3 -> 5
	TestTrue(TEXT("ring 1 aligned"), P.IsRingAligned(1));
	TestFalse(TEXT("bad index"), P.Rotate(7, 1));
	TestFalse(TEXT("not solved with one ring left"), P.IsSolved());
	P.Rotate(2, 3);
	TestTrue(TEXT("solved"), P.IsSolved());
	P.Rotate(2, 8);
	TestTrue(TEXT("a full turn keeps it solved"), P.IsSolved());
	return !HasAnyErrors();
}

#endif

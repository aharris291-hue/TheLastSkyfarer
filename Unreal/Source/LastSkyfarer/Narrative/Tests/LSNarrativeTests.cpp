// Automation tests: LastSkyfarer.Narrative.*
// Run: UnrealEditor-Cmd.exe LastSkyfarer.uproject -ExecCmds="Automation RunTests LastSkyfarer.Narrative; Quit" -unattended -nullrhi
// Mirrors Unreal/Tools/validate_narrative.py.

#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

#include "LSNarrativeTypes.h"
#include "LSStorySubsystem.h"
#include "Dom/JsonObject.h"
#include "Engine/GameInstance.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace LSNarrativeTest
{
	constexpr EAutomationTestFlags Flags = EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter;

	bool LoadDb(FAutomationTestBase& Test, FLSNarrativeDatabase& Db)
	{
		TArray<FString> Errors;
		const bool bOk = Db.LoadFromDirectory(FLSNarrativeDatabase::DefaultDataDir(), Errors);
		for (const FString& E : Errors) Test.AddError(E);
		return bOk;
	}

	ULSStorySubsystem* MakeStory(const FLSNarrativeDatabase& Db)
	{
		UGameInstance* GI = NewObject<UGameInstance>(GetTransientPackage());
		ULSStorySubsystem* Story = NewObject<ULSStorySubsystem>(GI);
		Story->InitWithDatabase(Db);
		return Story;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNarrativeDataTest, "LastSkyfarer.Narrative.DataLoadsAndResolves", LSNarrativeTest::Flags)
bool FLSNarrativeDataTest::RunTest(const FString& Parameters)
{
	FLSNarrativeDatabase Db;
	if (!LSNarrativeTest::LoadDb(*this, Db)) return false;

	TestTrue(TEXT("has conversations"), Db.Conversations.Num() >= 35);
	TestTrue(TEXT("has 4 Milestone A quests"), Db.Quests.Num() >= 4);
	for (const FString& E : Db.Validate()) AddError(E);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNarrativeCanonTest, "LastSkyfarer.Narrative.CanonLinesUnchanged", LSNarrativeTest::Flags)
bool FLSNarrativeCanonTest::RunTest(const FString& Parameters)
{
	FLSNarrativeDatabase Db;
	if (!LSNarrativeTest::LoadDb(*this, Db)) return false;

	// The archived Godot data sits at the repo root, next to Unreal/.
	const FString GodotDir = FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT(".."), TEXT("data"), TEXT("dialogue")));
	int32 Checked = 0;
	for (const TCHAR* File : { TEXT("windrest.json"), TEXT("workshop.json"), TEXT("sky.json") })
	{
		FString Json;
		if (!FFileHelper::LoadFileToString(Json, *FPaths::Combine(GodotDir, File)))
		{
			AddWarning(FString::Printf(TEXT("Godot source %s not found, canon check skipped"), File));
			continue;
		}
		TSharedPtr<FJsonObject> Root;
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
		{
			AddError(FString::Printf(TEXT("Could not parse %s"), File));
			continue;
		}
		for (const TPair<FString, TSharedPtr<FJsonValue>>& Conv : Root->Values)
		{
			const FLSConversation* Ours = Db.Conversations.Find(FName(*Conv.Key));
			const TArray<TSharedPtr<FJsonValue>>* Steps = nullptr;
			if (!Ours || !Conv.Value->TryGetArray(Steps)) continue;
			for (int32 i = 0; i < Steps->Num(); ++i)
			{
				const TSharedPtr<FJsonObject>* Step = nullptr;
				bool bCanon = false;
				if (!(*Steps)[i]->TryGetObject(Step) || !(*Step)->TryGetBoolField(TEXT("canon"), bCanon) || !bCanon) continue;
				++Checked;
				const FString Expected = (*Step)->GetStringField(TEXT("t"));
				if (!Ours->Lines.IsValidIndex(i) || Ours->Lines[i].Text.ToString() != Expected || !Ours->Lines[i].bCanon)
				{
					AddError(FString::Printf(TEXT("Canon line changed: %s[%d]"), *Conv.Key, i));
				}
			}
		}
	}
	AddInfo(FString::Printf(TEXT("%d canon lines checked"), Checked));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNarrativeRunTest, "LastSkyfarer.Narrative.MilestoneARun", LSNarrativeTest::Flags)
bool FLSNarrativeRunTest::RunTest(const FString& Parameters)
{
	FLSNarrativeDatabase Db;
	if (!LSNarrativeTest::LoadDb(*this, Db)) return false;
	ULSStorySubsystem* Story = LSNarrativeTest::MakeStory(Db);

	auto Talk = [Story](const TCHAR* Id) { Story->RunConversationInstant(FName(Id)); };

	// World triggers below stand in for level trigger volumes and pickups, as in the Godot levels.
	Talk(TEXT("opening"));
	Talk(TEXT("maren_intro"));
	for (const TCHAR* C : { TEXT("tavern_deliver"), TEXT("tessa_deliver"), TEXT("villager_deliver") }) Talk(C);
	Talk(TEXT("maren_return"));
	Talk(TEXT("maren_deed"));
	for (const TPair<FName, FLSJournalDef>& J : Db.Journal)
	{
		if (J.Value.Collectible == TEXT("elias_notes")) Story->AddJournal(J.Key);
	}
	Talk(TEXT("workshop_enter"));
	for (const TCHAR* C : { TEXT("inspect_maps"), TEXT("inspect_sketches"), TEXT("inspect_notes"), TEXT("search_done"),
		TEXT("compartment"), TEXT("final_entry"), TEXT("compass_awakens"), TEXT("workshop_leave_night") }) Talk(C);
	for (const TCHAR* C : { TEXT("piko_meeting"), TEXT("launch_ready"), TEXT("piko_found_wind"), TEXT("wind_refuses") }) Talk(C);

	for (const TPair<FName, FLSQuestDef>& Q : Db.Quests)
	{
		TestTrue(FString::Printf(TEXT("quest %s complete"), *Q.Key.ToString()), Story->GetQuestState(Q.Key) == ELSQuestState::Complete);
	}
	TestTrue(TEXT("demo_complete flag set"), Story->HasFlag(TEXT("demo_complete")));
	TestEqual(TEXT("chapter after the launch"), Story->GetChapter(), 3);
	for (const FString& P : Story->Problems) AddError(P);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNarrativeDialogueTest, "LastSkyfarer.Narrative.DialogueRunner", LSNarrativeTest::Flags)
bool FLSNarrativeDialogueTest::RunTest(const FString& Parameters)
{
	FLSNarrativeDatabase Db;
	if (!LSNarrativeTest::LoadDb(*this, Db)) return false;
	ULSStorySubsystem* Story = LSNarrativeTest::MakeStory(Db);

	const FLSConversation& Conv = Db.Conversations.FindChecked(TEXT("maren_intro"));
	int32 Spoken = 0;
	for (const FLSDialogueLine& L : Conv.Lines) Spoken += L.Text.IsEmpty() ? 0 : 1;

	Story->RunConversationInstant(TEXT("opening"));
	TestTrue(TEXT("starts"), Story->StartConversation(TEXT("maren_intro")));
	TestFalse(TEXT("refuses a second conversation"), Story->StartConversation(TEXT("opening")));
	Story->Problems.Reset();
	int32 Shown = 1;
	while (Story->IsInDialogue() && Shown < 1000)
	{
		Story->AdvanceDialogue();
		Shown += Story->IsInDialogue() ? 1 : 0;
	}
	TestEqual(TEXT("every spoken line shown once"), Shown, Spoken);
	TestFalse(TEXT("a quest is tracked"), Story->GetTrackedQuest().IsNone());
	TestEqual(TEXT("line actions ran (parcel given)"), Story->GetItemCount(TEXT("parcel_tavern")), 1);
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNarrativeConditionTest, "LastSkyfarer.Narrative.Conditions", LSNarrativeTest::Flags)
bool FLSNarrativeConditionTest::RunTest(const FString& Parameters)
{
	FLSNarrativeDatabase Db;
	if (!LSNarrativeTest::LoadDb(*this, Db)) return false;
	ULSStorySubsystem* Story = LSNarrativeTest::MakeStory(Db);

	TestTrue(TEXT("empty is true"), Story->Check(TEXT("")));
	TestFalse(TEXT("unset flag"), Story->Check(TEXT("test_flag")));
	Story->SetFlag(TEXT("test_flag"));
	TestTrue(TEXT("set flag"), Story->Check(TEXT("test_flag")));
	TestFalse(TEXT("negated flag"), Story->Check(TEXT("!test_flag")));
	TestTrue(TEXT("time of day"), Story->Check(TEXT("tod:morning")));

	TArray<FName> QuestIds;
	Db.Quests.GetKeys(QuestIds);
	const FName Q = QuestIds[0];
	const FString QS = Q.ToString();
	TestTrue(TEXT("quest none"), Story->Check(FString::Printf(TEXT("quest:%s:none"), *QS)));
	Story->StartQuest(Q);
	TestTrue(TEXT("quest active"), Story->Check(FString::Printf(TEXT("quest:%s:active"), *QS)));
	Story->CompleteQuest(Q);
	TestTrue(TEXT("quest complete"), Story->Check(FString::Printf(TEXT("quest:%s:complete"), *QS)));
	const FName O = Db.Quests[Q].Objectives[0].Id;
	TestTrue(TEXT("objectives of a complete quest count as done"), Story->Check(FString::Printf(TEXT("obj:%s:%s"), *QS, *O.ToString())));
	return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FLSNarrativeSaveTest, "LastSkyfarer.Narrative.SaveRoundTripAndBackup", LSNarrativeTest::Flags)
bool FLSNarrativeSaveTest::RunTest(const FString& Parameters)
{
	FLSNarrativeDatabase Db;
	if (!LSNarrativeTest::LoadDb(*this, Db)) return false;
	ULSStorySubsystem* Story = LSNarrativeTest::MakeStory(Db);
	const FString Slot = TEXT("automation_test");
	IFileManager& FM = IFileManager::Get();
	const FString Path = ULSStorySubsystem::SlotPath(Slot);

	Story->SetFlag(TEXT("first"));
	TestTrue(TEXT("first save"), Story->SaveToSlot(Slot));
	Story->SetFlag(TEXT("second"));
	TestTrue(TEXT("second save"), Story->SaveToSlot(Slot));
	TestTrue(TEXT("backup kept"), FM.FileExists(*(Path + TEXT(".bak"))));

	Story->NewGame();
	TestTrue(TEXT("loads"), Story->LoadFromSlot(Slot));
	TestTrue(TEXT("latest state restored"), Story->HasFlag(TEXT("second")));

	// Corrupt the main file: loading must fall back to the backup (the first save).
	FFileHelper::SaveStringToFile(TEXT("not a save"), *Path);
	Story->NewGame();
	TestTrue(TEXT("recovers from backup"), Story->LoadFromSlot(Slot));
	TestTrue(TEXT("backup state"), Story->HasFlag(TEXT("first")) && !Story->HasFlag(TEXT("second")));

	FM.Delete(*Path);
	FM.Delete(*(Path + TEXT(".bak")));
	return !HasAnyErrors();
}

#endif

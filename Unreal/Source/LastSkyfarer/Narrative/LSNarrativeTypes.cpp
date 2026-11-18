#include "LSNarrativeTypes.h"

#include "JsonObjectConverter.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
	template <typename TFile>
	bool LoadFile(const FString& Dir, const TCHAR* Name, TFile& Out, TArray<FString>& Errors)
	{
		const FString Path = FPaths::Combine(Dir, Name);
		FString Json;
		if (!FFileHelper::LoadFileToString(Json, *Path))
		{
			Errors.Add(FString::Printf(TEXT("Missing data file %s"), *Path));
			return false;
		}
		if (!FJsonObjectConverter::JsonObjectStringToUStruct(Json, &Out, 0, 0))
		{
			Errors.Add(FString::Printf(TEXT("Malformed data file %s"), *Path));
			return false;
		}
		return true;
	}

	template <typename TDef>
	void Index(const TArray<TDef>& In, TMap<FName, TDef>& Out, const TCHAR* What, TArray<FString>& Errors)
	{
		for (const TDef& Def : In)
		{
			if (Out.Contains(Def.Id))
			{
				Errors.Add(FString::Printf(TEXT("Duplicate %s id %s"), What, *Def.Id.ToString()));
			}
			Out.Add(Def.Id, Def);
		}
	}
}

FString FLSNarrativeDatabase::DefaultDataDir()
{
	return FPaths::Combine(FPaths::ProjectContentDir(), TEXT("LastSkyfarer"), TEXT("Data"));
}

bool FLSNarrativeDatabase::LoadFromDirectory(const FString& Dir, TArray<FString>& OutErrors)
{
	*this = FLSNarrativeDatabase();
	const int32 ErrorsBefore = OutErrors.Num();

	FLSConversationFile Conv;
	FLSQuestFile Quest;
	FLSJournalFile Jour;
	FLSItemFile Item;
	FLSSpeakerFile Speak;
	FLSLocationFile Loc;
	FLSStoryEventFile Ev;

	if (LoadFile(Dir, TEXT("Conversations.json"), Conv, OutErrors)) Index(Conv.Conversations, Conversations, TEXT("conversation"), OutErrors);
	if (LoadFile(Dir, TEXT("Quests.json"), Quest, OutErrors)) Index(Quest.Quests, Quests, TEXT("quest"), OutErrors);
	if (LoadFile(Dir, TEXT("Journal.json"), Jour, OutErrors)) Index(Jour.Entries, Journal, TEXT("journal entry"), OutErrors);
	if (LoadFile(Dir, TEXT("Items.json"), Item, OutErrors)) Index(Item.Items, Items, TEXT("item"), OutErrors);
	if (LoadFile(Dir, TEXT("Speakers.json"), Speak, OutErrors)) Index(Speak.Speakers, Speakers, TEXT("speaker"), OutErrors);
	if (LoadFile(Dir, TEXT("Locations.json"), Loc, OutErrors)) Index(Loc.Locations, Locations, TEXT("location"), OutErrors);
	if (LoadFile(Dir, TEXT("StoryEvents.json"), Ev, OutErrors))
	{
		Index(Ev.Events, Events, TEXT("event"), OutErrors);
		for (const FLSCollectibleObjective& C : Ev.CollectibleObjectives)
		{
			CollectibleObjectives.Add(C.Group, C.Objective);
		}
	}
	return OutErrors.Num() == ErrorsBefore;
}

const FLSObjectiveDef* FLSNarrativeDatabase::FindObjective(FName QuestId, FName ObjectiveId) const
{
	if (const FLSQuestDef* Q = Quests.Find(QuestId))
	{
		return Q->Objectives.FindByPredicate([ObjectiveId](const FLSObjectiveDef& O) { return O.Id == ObjectiveId; });
	}
	return nullptr;
}

TArray<FString> FLSNarrativeDatabase::Validate() const
{
	TArray<FString> Errors;

	auto CheckObjectiveRef = [this, &Errors](const FString& Ref, const FString& Where)
	{
		FString Q, O;
		if (!Ref.Split(TEXT(":"), &Q, &O) || !FindObjective(FName(*Q), FName(*O)))
		{
			Errors.Add(FString::Printf(TEXT("%s: unknown objective %s"), *Where, *Ref));
		}
	};

	auto CheckActions = [&](const TArray<FLSStoryAction>& Actions, const FString& Where)
	{
		for (const FLSStoryAction& A : Actions)
		{
			const FName Arg(*A.Arg);
			switch (A.Type)
			{
			case ELSActionType::StartQuest:
			case ELSActionType::CompleteQuest:
				if (!Quests.Contains(Arg)) Errors.Add(FString::Printf(TEXT("%s: unknown quest %s"), *Where, *A.Arg));
				break;
			case ELSActionType::AdvanceObjective:
				CheckObjectiveRef(A.Arg, Where);
				break;
			case ELSActionType::GiveItem:
			case ELSActionType::TakeItem:
				if (!Items.Contains(Arg)) Errors.Add(FString::Printf(TEXT("%s: unknown item %s"), *Where, *A.Arg));
				break;
			case ELSActionType::AddJournal:
				if (!Journal.Contains(Arg)) Errors.Add(FString::Printf(TEXT("%s: unknown journal entry %s"), *Where, *A.Arg));
				break;
			default:
				break;
			}
		}
	};

	for (const TPair<FName, FLSConversation>& C : Conversations)
	{
		for (int32 i = 0; i < C.Value.Lines.Num(); ++i)
		{
			const FLSDialogueLine& L = C.Value.Lines[i];
			const FString Where = FString::Printf(TEXT("%s[%d]"), *C.Key.ToString(), i);
			if (!L.Text.IsEmpty() && !Speakers.Contains(L.Speaker))
			{
				Errors.Add(FString::Printf(TEXT("%s: unknown speaker %s"), *Where, *L.Speaker.ToString()));
			}
			CheckActions(L.Actions, Where);
		}
	}
	for (const TPair<FName, FLSQuestDef>& Q : Quests)
	{
		for (const FName& R : Q.Value.Rewards)
		{
			if (!Items.Contains(R)) Errors.Add(FString::Printf(TEXT("quest %s: unknown reward %s"), *Q.Key.ToString(), *R.ToString()));
		}
	}
	for (const TPair<FName, FLSStoryEventDef>& E : Events)
	{
		CheckActions(E.Value.Actions, FString::Printf(TEXT("event %s"), *E.Key.ToString()));
	}
	for (const TPair<FName, FString>& C : CollectibleObjectives)
	{
		CheckObjectiveRef(C.Value, FString::Printf(TEXT("collectible group %s"), *C.Key.ToString()));
		bool bHasEntry = false;
		for (const TPair<FName, FLSJournalDef>& J : Journal)
		{
			bHasEntry |= (J.Value.Collectible == C.Key);
		}
		if (!bHasEntry) Errors.Add(FString::Printf(TEXT("collectible group %s has no journal entries"), *C.Key.ToString()));
	}
	return Errors;
}

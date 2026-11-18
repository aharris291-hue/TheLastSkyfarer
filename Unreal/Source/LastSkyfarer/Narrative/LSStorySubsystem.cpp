#include "LSStorySubsystem.h"

#include "LSSaveGame.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

DEFINE_LOG_CATEGORY_STATIC(LogLSStory, Log, All);

namespace
{
	// Save files are wrapped as [magic][payload size][CRC32][payload]. UGameplayStatics::LoadGameFromMemory
	// does not validate its input and asserts on garbage, so a file is only handed to it after this check.
	constexpr uint32 SaveMagic = 0x5653534C; // "LSSV"
	constexpr int32 SaveHeaderSize = 3 * sizeof(uint32);

	void WrapSave(const TArray<uint8>& Payload, TArray<uint8>& Out)
	{
		const uint32 Header[3] = { SaveMagic, static_cast<uint32>(Payload.Num()), FCrc::MemCrc32(Payload.GetData(), Payload.Num()) };
		Out.Reset(SaveHeaderSize + Payload.Num());
		Out.Append(reinterpret_cast<const uint8*>(Header), SaveHeaderSize);
		Out.Append(Payload);
	}

	bool UnwrapSave(const TArray<uint8>& In, TArray<uint8>& OutPayload)
	{
		if (In.Num() < SaveHeaderSize) return false;
		uint32 Header[3];
		FMemory::Memcpy(Header, In.GetData(), SaveHeaderSize);
		if (Header[0] != SaveMagic || Header[1] != static_cast<uint32>(In.Num() - SaveHeaderSize)) return false;
		if (FCrc::MemCrc32(In.GetData() + SaveHeaderSize, Header[1]) != Header[2]) return false;
		OutPayload = TArray<uint8>(In.GetData() + SaveHeaderSize, Header[1]);
		return true;
	}

	bool SplitObjectiveRef(const FString& Ref, FName& OutQuest, FName& OutObjective)
	{
		FString Q, O;
		if (!Ref.Split(TEXT(":"), &Q, &O)) return false;
		OutQuest = FName(*Q);
		OutObjective = FName(*O);
		return true;
	}

	const TCHAR* QuestStateName(ELSQuestState S)
	{
		switch (S)
		{
		case ELSQuestState::Active: return TEXT("active");
		case ELSQuestState::Complete: return TEXT("complete");
		default: return TEXT("none");
		}
	}
}

ULSStorySubsystem* ULSStorySubsystem::Get(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	return GI ? GI->GetSubsystem<ULSStorySubsystem>() : nullptr;
}

void ULSStorySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	TArray<FString> Errors;
	if (!Database.LoadFromDirectory(FLSNarrativeDatabase::DefaultDataDir(), Errors))
	{
		for (const FString& E : Errors) Report(E);
	}
	for (const FString& E : Database.Validate()) Report(E);

	UE_LOG(LogLSStory, Log, TEXT("Narrative data: %d conversations, %d quests, %d journal entries, %d items"),
		Database.Conversations.Num(), Database.Quests.Num(), Database.Journal.Num(), Database.Items.Num());

	NewGame();
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &ULSStorySubsystem::Tick));
}

void ULSStorySubsystem::Deinitialize()
{
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
	Super::Deinitialize();
}

void ULSStorySubsystem::InitWithDatabase(const FLSNarrativeDatabase& InDatabase)
{
	Database = InDatabase;
	Problems.Reset();
	NewGame();
}

void ULSStorySubsystem::NewGame()
{
	State = FLSStorySaveData();
	ActiveConversation = NAME_None;
	LineIndex = INDEX_NONE;
}

bool ULSStorySubsystem::Tick(float DeltaTime)
{
	const UGameInstance* GI = GetGameInstance();
	const UWorld* World = GI ? GI->GetWorld() : nullptr;
	if (World && World->IsGameWorld() && !World->IsPaused())
	{
		State.PlaytimeSeconds += DeltaTime;
	}
	return true;
}

void ULSStorySubsystem::Report(const FString& Problem)
{
	UE_LOG(LogLSStory, Warning, TEXT("%s"), *Problem);
	Problems.Add(Problem);
}

// ---------------------------------------------------------------- conditions

bool ULSStorySubsystem::Check(const FString& Condition) const
{
	FString C = Condition.TrimStartAndEnd();
	if (C.IsEmpty()) return true;
	if (C.StartsWith(TEXT("!"))) return !Check(C.Mid(1));

	TArray<FString> Parts;
	C.ParseIntoArray(Parts, TEXT(":"));
	if (Parts.Num() == 2 && Parts[0] == TEXT("item")) return GetItemCount(FName(*Parts[1])) > 0;
	if (Parts.Num() == 2 && Parts[0] == TEXT("tod")) return State.TimeOfDay.ToString().Equals(Parts[1], ESearchCase::IgnoreCase);
	if (Parts.Num() == 3 && Parts[0] == TEXT("quest")) return Parts[2].Equals(QuestStateName(GetQuestState(FName(*Parts[1]))), ESearchCase::IgnoreCase);
	if (Parts.Num() == 3 && Parts[0] == TEXT("obj")) return IsObjectiveDone(FName(*Parts[1]), FName(*Parts[2]));
	return HasFlag(FName(*C));
}

bool ULSStorySubsystem::CheckAll(const TArray<FString>& Conditions) const
{
	for (const FString& C : Conditions)
	{
		if (!Check(C)) return false;
	}
	return true;
}

// ---------------------------------------------------------------- actions

void ULSStorySubsystem::RunActions(const TArray<FLSStoryAction>& Actions)
{
	for (const FLSStoryAction& A : Actions)
	{
		RunAction(A.Type, A.Arg, A.Amount);
	}
}

void ULSStorySubsystem::RunAction(ELSActionType Type, const FString& Arg, int32 Amount)
{
	const FName Name(*Arg);
	switch (Type)
	{
	case ELSActionType::SetFlag: SetFlag(Name, true); break;
	case ELSActionType::ClearFlag: SetFlag(Name, false); break;
	case ELSActionType::GiveItem: GiveItem(Name, Amount); break;
	case ELSActionType::TakeItem: TakeItem(Name, Amount); break;
	case ELSActionType::StartQuest: StartQuest(Name); break;
	case ELSActionType::AdvanceObjective:
	{
		FName Q, O;
		if (SplitObjectiveRef(Arg, Q, O)) AdvanceObjective(Q, O, Amount);
		else Report(FString::Printf(TEXT("Bad objective reference %s"), *Arg));
		break;
	}
	case ELSActionType::CompleteQuest: CompleteQuest(Name); break;
	case ELSActionType::AddJournal: AddJournal(Name); break;
	case ELSActionType::Event: FireEvent(Name); break;
	case ELSActionType::TimeOfDay: SetTimeOfDay(Name); break;
	case ELSActionType::Chapter: SetChapter(Amount); break;
	case ELSActionType::Autosave: SaveToSlot(TEXT("autosave")); break;
	case ELSActionType::Sfx: OnSfx.Broadcast(Name); break;
	}
}

void ULSStorySubsystem::SetFlag(FName Flag, bool bSet)
{
	const bool bHad = State.Flags.Contains(Flag);
	if (bSet == bHad) return;
	if (bSet) State.Flags.Add(Flag);
	else State.Flags.Remove(Flag);
	OnFlagChanged.Broadcast(Flag, bSet);
}

int32 ULSStorySubsystem::GetItemCount(FName Item) const
{
	const int32* N = State.Inventory.Find(Item);
	return N ? *N : 0;
}

void ULSStorySubsystem::GiveItem(FName Item, int32 Amount)
{
	State.Inventory.FindOrAdd(Item) += FMath::Max(Amount, 1);
	if (const FLSItemDef* Def = Database.Items.Find(Item))
	{
		OnNotify.Broadcast(FText::Format(NSLOCTEXT("LS", "GotItem", "Received: {0}"), Def->Name));
	}
}

bool ULSStorySubsystem::TakeItem(FName Item, int32 Amount)
{
	int32* N = State.Inventory.Find(Item);
	if (!N || *N < Amount)
	{
		Report(FString::Printf(TEXT("TakeItem %s x%d without having it"), *Item.ToString(), Amount));
		return false;
	}
	*N -= Amount;
	if (*N <= 0) State.Inventory.Remove(Item);
	return true;
}

// ---------------------------------------------------------------- quests

ELSQuestState ULSStorySubsystem::GetQuestState(FName Quest) const
{
	const FLSQuestProgress* P = State.Quests.Find(Quest);
	return P ? P->State : ELSQuestState::None;
}

int32 ULSStorySubsystem::GetObjectiveProgress(FName Quest, FName Objective) const
{
	if (const FLSQuestProgress* P = State.Quests.Find(Quest))
	{
		if (const int32* N = P->Objectives.Find(Objective)) return *N;
	}
	return 0;
}

bool ULSStorySubsystem::IsObjectiveDone(FName Quest, FName Objective) const
{
	if (GetQuestState(Quest) == ELSQuestState::Complete) return true;
	const FLSObjectiveDef* Def = Database.FindObjective(Quest, Objective);
	return Def && GetObjectiveProgress(Quest, Objective) >= Def->Count;
}

TArray<FLSObjectiveDef> ULSStorySubsystem::GetVisibleObjectives(FName Quest) const
{
	TArray<FLSObjectiveDef> Out;
	if (const FLSQuestDef* Q = Database.Quests.Find(Quest))
	{
		for (const FLSObjectiveDef& O : Q->Objectives)
		{
			if (CheckAll(O.HiddenUntil)) Out.Add(O);
		}
	}
	return Out;
}

void ULSStorySubsystem::SetTrackedQuest(FName Quest)
{
	State.TrackedQuest = Quest;
}

void ULSStorySubsystem::StartQuest(FName Quest)
{
	const FLSQuestDef* Def = Database.Quests.Find(Quest);
	if (!Def)
	{
		Report(FString::Printf(TEXT("StartQuest: unknown quest %s"), *Quest.ToString()));
		return;
	}
	if (GetQuestState(Quest) != ELSQuestState::None) return;

	FLSQuestProgress& P = State.Quests.Add(Quest);
	P.State = ELSQuestState::Active;
	if (Def->bMain || State.TrackedQuest.IsNone()) State.TrackedQuest = Quest;

	OnNotify.Broadcast(FText::Format(NSLOCTEXT("LS", "QuestStarted", "New quest: {0}"), Def->Title));
	OnQuestChanged.Broadcast(Quest, ELSQuestState::Active);
}

void ULSStorySubsystem::AdvanceObjective(FName Quest, FName Objective, int32 Amount)
{
	const FLSObjectiveDef* Def = Database.FindObjective(Quest, Objective);
	if (!Def)
	{
		Report(FString::Printf(TEXT("AdvanceObjective: unknown objective %s:%s"), *Quest.ToString(), *Objective.ToString()));
		return;
	}
	if (GetQuestState(Quest) != ELSQuestState::Active)
	{
		UE_LOG(LogLSStory, Verbose, TEXT("Objective %s:%s ignored, quest not active"), *Quest.ToString(), *Objective.ToString());
		return;
	}
	int32& N = State.Quests[Quest].Objectives.FindOrAdd(Objective);
	const int32 Before = N;
	N = FMath::Min(N + FMath::Max(Amount, 1), Def->Count);
	if (N != Before)
	{
		if (N >= Def->Count) OnNotify.Broadcast(FText::Format(NSLOCTEXT("LS", "ObjectiveDone", "Done: {0}"), Def->Text));
		OnQuestChanged.Broadcast(Quest, ELSQuestState::Active);
	}
	TryAutoComplete(Quest);
}

void ULSStorySubsystem::TryAutoComplete(FName Quest)
{
	const FLSQuestDef* Def = Database.Quests.Find(Quest);
	if (!Def || !Def->bAutoComplete || GetQuestState(Quest) != ELSQuestState::Active) return;
	for (const FLSObjectiveDef& O : Def->Objectives)
	{
		if (!O.bOptional && !IsObjectiveDone(Quest, O.Id)) return;
	}
	CompleteQuest(Quest);
}

void ULSStorySubsystem::CompleteQuest(FName Quest)
{
	const FLSQuestDef* Def = Database.Quests.Find(Quest);
	if (!Def || GetQuestState(Quest) != ELSQuestState::Active) return;

	State.Quests[Quest].State = ELSQuestState::Complete;
	for (const FName& R : Def->Rewards) GiveItem(R, 1);

	if (State.TrackedQuest == Quest)
	{
		// Track the next active quest, main quests first.
		State.TrackedQuest = NAME_None;
		for (int32 Pass = 0; Pass < 2 && State.TrackedQuest.IsNone(); ++Pass)
		{
			for (const TPair<FName, FLSQuestProgress>& P : State.Quests)
			{
				const FLSQuestDef* Other = Database.Quests.Find(P.Key);
				if (P.Value.State == ELSQuestState::Active && Other && (Pass == 1 || Other->bMain))
				{
					State.TrackedQuest = P.Key;
					break;
				}
			}
		}
	}
	OnNotify.Broadcast(FText::Format(NSLOCTEXT("LS", "QuestDone", "Quest complete: {0}"), Def->Title));
	OnQuestChanged.Broadcast(Quest, ELSQuestState::Complete);
}

// ---------------------------------------------------------------- journal and world

void ULSStorySubsystem::AddJournal(FName Entry)
{
	const FLSJournalDef* Def = Database.Journal.Find(Entry);
	if (!Def)
	{
		Report(FString::Printf(TEXT("AddJournal: unknown entry %s"), *Entry.ToString()));
		return;
	}
	if (State.Journal.Contains(Entry)) return;
	State.Journal.Add(Entry);
	OnNotify.Broadcast(FText::Format(NSLOCTEXT("LS", "JournalAdded", "Journal: {0}"), Def->Title));
	OnJournalAdded.Broadcast(Entry);

	if (const FString* Ref = Database.CollectibleObjectives.Find(Def->Collectible))
	{
		FName Q, O;
		if (SplitObjectiveRef(*Ref, Q, O) && GetQuestState(Q) == ELSQuestState::Active)
		{
			AdvanceObjective(Q, O, 1);
		}
	}
}

void ULSStorySubsystem::DiscoverLocation(FName Location)
{
	if (State.Discovered.Contains(Location)) return;
	State.Discovered.Add(Location);
	if (const FLSLocationDef* Def = Database.Locations.Find(Location))
	{
		OnNotify.Broadcast(Def->Name);
	}
}

ELSMapKnowledge ULSStorySubsystem::GetMapKnowledge(FName Location) const
{
	if (State.Discovered.Contains(Location)) return ELSMapKnowledge::Known;
	if (HasFlag(FName(*FString::Printf(TEXT("heard_%s"), *Location.ToString())))) return ELSMapKnowledge::Rumoured;
	return ELSMapKnowledge::Unknown;
}

void ULSStorySubsystem::AddMapPin(const FVector& WorldLocation)
{
	if (State.MapPins.Num() >= MaxMapPins) State.MapPins.RemoveAt(0);
	State.MapPins.Add(WorldLocation);
}

void ULSStorySubsystem::RemoveMapPin(int32 Index)
{
	if (State.MapPins.IsValidIndex(Index)) State.MapPins.RemoveAt(Index);
}

void ULSStorySubsystem::SetTimeOfDay(FName TimeOfDay)
{
	if (State.TimeOfDay == TimeOfDay) return;
	State.TimeOfDay = TimeOfDay;
	OnTimeOfDayChanged.Broadcast(TimeOfDay);
}

void ULSStorySubsystem::SetChapter(int32 Chapter)
{
	if (State.Chapter == Chapter) return;
	State.Chapter = Chapter;
	OnChapterChanged.Broadcast(Chapter);
}

void ULSStorySubsystem::FireEvent(FName Event)
{
	if (const FLSStoryEventDef* Def = Database.Events.Find(Event))
	{
		RunActions(Def->Actions);
	}
	OnStoryEvent.Broadcast(Event);
}

// ---------------------------------------------------------------- dialogue

bool ULSStorySubsystem::StartConversation(FName Conversation)
{
	if (IsInDialogue())
	{
		Report(FString::Printf(TEXT("StartConversation %s while %s is running"), *Conversation.ToString(), *ActiveConversation.ToString()));
		return false;
	}
	if (!Database.Conversations.Contains(Conversation))
	{
		Report(FString::Printf(TEXT("StartConversation: unknown conversation %s"), *Conversation.ToString()));
		return false;
	}
	ActiveConversation = Conversation;
	LineIndex = INDEX_NONE;
	ShowNextLine();
	return true;
}

void ULSStorySubsystem::AdvanceDialogue()
{
	if (IsInDialogue()) ShowNextLine();
}

void ULSStorySubsystem::ShowNextLine()
{
	const FLSConversation& Conv = Database.Conversations[ActiveConversation];
	while (++LineIndex < Conv.Lines.Num())
	{
		const FLSDialogueLine& Line = Conv.Lines[LineIndex];
		RunActions(Line.Actions);
		if (!Line.Text.IsEmpty())
		{
			OnDialogueLine.Broadcast(ActiveConversation, Line);
			return;
		}
	}
	const FName Ended = ActiveConversation;
	ActiveConversation = NAME_None;
	LineIndex = INDEX_NONE;
	OnDialogueEnded.Broadcast(Ended);
}

void ULSStorySubsystem::RunConversationInstant(FName Conversation)
{
	if (const FLSConversation* Conv = Database.Conversations.Find(Conversation))
	{
		for (const FLSDialogueLine& Line : Conv->Lines) RunActions(Line.Actions);
	}
	else
	{
		Report(FString::Printf(TEXT("RunConversationInstant: unknown conversation %s"), *Conversation.ToString()));
	}
}

// ---------------------------------------------------------------- saves

FString ULSStorySubsystem::SlotPath(const FString& Slot)
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("SaveGames"), Slot + TEXT(".sav"));
}

bool ULSStorySubsystem::DoesSlotExist(const FString& Slot)
{
	IFileManager& FM = IFileManager::Get();
	return FM.FileExists(*SlotPath(Slot)) || FM.FileExists(*(SlotPath(Slot) + TEXT(".bak")));
}

bool ULSStorySubsystem::SaveToSlot(const FString& Slot)
{
	ULSSaveGame* Save = NewObject<ULSSaveGame>();
	Save->Data = State;
	Save->Data.Version = FLSStorySaveData::CurrentVersion;
	Save->SavedAt = FDateTime::UtcNow();

	if (const UGameInstance* GI = GetGameInstance())
	{
		if (UWorld* World = GI->GetWorld())
		{
			Save->Data.MapName = FName(*UGameplayStatics::GetCurrentLevelName(World));
			if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(World, 0))
			{
				Save->Data.PlayerTransform = Pawn->GetActorTransform();
			}
		}
	}

	TArray<uint8> Payload, Bytes;
	if (!UGameplayStatics::SaveGameToMemory(Save, Payload))
	{
		Report(TEXT("Save failed: could not serialize"));
		return false;
	}
	WrapSave(Payload, Bytes);

	IFileManager& FM = IFileManager::Get();
	const FString Path = SlotPath(Slot);
	const FString Tmp = Path + TEXT(".tmp");
	const FString Bak = Path + TEXT(".bak");

	if (!FFileHelper::SaveArrayToFile(Bytes, *Tmp))
	{
		Report(FString::Printf(TEXT("Save failed: could not write %s"), *Tmp));
		return false;
	}
	if (FM.FileExists(*Path) && !FM.Move(*Bak, *Path, /*bReplace*/ true))
	{
		Report(FString::Printf(TEXT("Save: could not back up %s"), *Path));
	}
	if (!FM.Move(*Path, *Tmp, /*bReplace*/ true))
	{
		Report(FString::Printf(TEXT("Save failed: could not move %s into place"), *Tmp));
		return false;
	}
	UE_LOG(LogLSStory, Log, TEXT("Saved %s"), *Path);
	return true;
}

bool ULSStorySubsystem::LoadFromSlot(const FString& Slot)
{
	const FString Path = SlotPath(Slot);
	for (const FString& Candidate : { Path, Path + TEXT(".bak") })
	{
		TArray<uint8> Bytes, Payload;
		if (!FFileHelper::LoadFileToArray(Bytes, *Candidate, FILEREAD_Silent) || Bytes.Num() == 0) continue;
		if (!UnwrapSave(Bytes, Payload))
		{
			UE_LOG(LogLSStory, Warning, TEXT("Save file %s failed its integrity check"), *Candidate);
			continue;
		}

		ULSSaveGame* Save = Cast<ULSSaveGame>(UGameplayStatics::LoadGameFromMemory(Payload));
		if (!Save || Save->Data.Version > FLSStorySaveData::CurrentVersion)
		{
			UE_LOG(LogLSStory, Warning, TEXT("Save file %s is corrupt or from a newer version"), *Candidate);
			continue;
		}
		State = Save->Data;
		ActiveConversation = NAME_None;
		LineIndex = INDEX_NONE;
		OnTimeOfDayChanged.Broadcast(State.TimeOfDay);
		OnChapterChanged.Broadcast(State.Chapter);
		UE_LOG(LogLSStory, Log, TEXT("Loaded %s"), *Candidate);
		return true;
	}
	return false;
}

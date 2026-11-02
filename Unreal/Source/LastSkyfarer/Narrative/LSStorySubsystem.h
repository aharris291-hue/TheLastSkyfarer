// The Last Skyfarer: story state, dialogue runner, quests, journal, inventory and saves.
// Rules mirror the Godot demo's managers (see docs/unreal/GODOT_REUSE.md) and
// Unreal/Tools/validate_narrative.py.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "LSNarrativeTypes.h"
#include "LSStorySubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLSOnDialogueLine, FName, ConversationId, const FLSDialogueLine&, Line);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnDialogueEnded, FName, ConversationId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnStoryEvent, FName, EventId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnTimeOfDayChanged, FName, TimeOfDay);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnNotify, const FText&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLSOnQuestChanged, FName, QuestId, ELSQuestState, State);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnJournalAdded, FName, EntryId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLSOnFlagChanged, FName, Flag, bool, bSet);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnSfx, FName, SfxId);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnChapterChanged, int32, Chapter);

UCLASS()
class LASTSKYFARER_API ULSStorySubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	/** The story subsystem of the world's game instance, or null (e.g. in a bare test world). */
	static ULSStorySubsystem* Get(const UObject* WorldContext);

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** For automation tests: use this database instead of loading from disk. */
	void InitWithDatabase(const FLSNarrativeDatabase& InDatabase);

	const FLSNarrativeDatabase& GetDatabase() const { return Database; }
	const FLSStorySaveData& GetState() const { return State; }

	UFUNCTION(BlueprintCallable, Category = "Story")
	void NewGame();

	// ---- Conditions and actions ----

	/** "flag", "!flag", "item:id", "quest:id:none|active|complete", "obj:quest:objective", "tod:Morning". */
	UFUNCTION(BlueprintPure, Category = "Story")
	bool Check(const FString& Condition) const;

	/** True if every condition holds (empty = true). */
	UFUNCTION(BlueprintPure, Category = "Story")
	bool CheckAll(const TArray<FString>& Conditions) const;

	UFUNCTION(BlueprintCallable, Category = "Story")
	void RunActions(const TArray<FLSStoryAction>& Actions);

	UFUNCTION(BlueprintCallable, Category = "Story")
	void RunAction(ELSActionType Type, const FString& Arg, int32 Amount = 1);

	// ---- Flags, items ----

	UFUNCTION(BlueprintPure, Category = "Story") bool HasFlag(FName Flag) const { return State.Flags.Contains(Flag); }
	UFUNCTION(BlueprintCallable, Category = "Story") void SetFlag(FName Flag, bool bSet = true);
	UFUNCTION(BlueprintPure, Category = "Story") int32 GetItemCount(FName Item) const;
	UFUNCTION(BlueprintCallable, Category = "Story") void GiveItem(FName Item, int32 Amount = 1);
	UFUNCTION(BlueprintCallable, Category = "Story") bool TakeItem(FName Item, int32 Amount = 1);

	// ---- Quests ----

	UFUNCTION(BlueprintPure, Category = "Story") ELSQuestState GetQuestState(FName Quest) const;
	UFUNCTION(BlueprintPure, Category = "Story") int32 GetObjectiveProgress(FName Quest, FName Objective) const;
	UFUNCTION(BlueprintPure, Category = "Story") bool IsObjectiveDone(FName Quest, FName Objective) const;
	/** Objectives whose HiddenUntil conditions all hold. */
	UFUNCTION(BlueprintPure, Category = "Story") TArray<FLSObjectiveDef> GetVisibleObjectives(FName Quest) const;
	UFUNCTION(BlueprintPure, Category = "Story") FName GetTrackedQuest() const { return State.TrackedQuest; }
	UFUNCTION(BlueprintCallable, Category = "Story") void SetTrackedQuest(FName Quest);
	UFUNCTION(BlueprintCallable, Category = "Story") void StartQuest(FName Quest);
	/** Ignored (with a log line) when the quest is not active, as in the Godot demo. */
	UFUNCTION(BlueprintCallable, Category = "Story") void AdvanceObjective(FName Quest, FName Objective, int32 Amount = 1);
	UFUNCTION(BlueprintCallable, Category = "Story") void CompleteQuest(FName Quest);

	// ---- Journal, world ----

	UFUNCTION(BlueprintCallable, Category = "Story") void AddJournal(FName Entry);
	UFUNCTION(BlueprintPure, Category = "Story") bool HasJournal(FName Entry) const { return State.Journal.Contains(Entry); }
	UFUNCTION(BlueprintCallable, Category = "Story") void DiscoverLocation(FName Location);
	/** Known if discovered, Rumoured if the flag heard_<id> is set, otherwise Unknown. */
	UFUNCTION(BlueprintPure, Category = "Story") ELSMapKnowledge GetMapKnowledge(FName Location) const;

	static constexpr int32 MaxMapPins = 3;
	/** Adds a pin; when all 3 are used, the oldest is replaced. */
	UFUNCTION(BlueprintCallable, Category = "Map") void AddMapPin(const FVector& WorldLocation);
	UFUNCTION(BlueprintCallable, Category = "Map") void RemoveMapPin(int32 Index);
	UFUNCTION(BlueprintPure, Category = "Map") const TArray<FVector>& GetMapPins() const { return State.MapPins; }
	UFUNCTION(BlueprintCallable, Category = "Story") void SetTimeOfDay(FName TimeOfDay);
	UFUNCTION(BlueprintPure, Category = "Story") FName GetTimeOfDay() const { return State.TimeOfDay; }
	UFUNCTION(BlueprintCallable, Category = "Story") void SetChapter(int32 Chapter);
	UFUNCTION(BlueprintPure, Category = "Story") int32 GetChapter() const { return State.Chapter; }
	UFUNCTION(BlueprintCallable, Category = "Story") void FireEvent(FName Event);

	// ---- Dialogue ----

	/** Starts a conversation and shows its first spoken line. False if unknown or one is already running. */
	UFUNCTION(BlueprintCallable, Category = "Dialogue") bool StartConversation(FName Conversation);
	/** Shows the next spoken line, running each line's actions as it is reached. Ends the conversation after the last. */
	UFUNCTION(BlueprintCallable, Category = "Dialogue") void AdvanceDialogue();
	UFUNCTION(BlueprintPure, Category = "Dialogue") bool IsInDialogue() const { return !ActiveConversation.IsNone(); }
	/** Runs a whole conversation instantly (actions only). Used by tests and skip. */
	UFUNCTION(BlueprintCallable, Category = "Dialogue") void RunConversationInstant(FName Conversation);

	// ---- Saves (atomic: temp file, then swap, previous kept as .bak) ----

	UFUNCTION(BlueprintCallable, Category = "Save") bool SaveToSlot(const FString& Slot);
	/** Falls back to the .bak copy if the main file is missing or corrupt. */
	UFUNCTION(BlueprintCallable, Category = "Save") bool LoadFromSlot(const FString& Slot);
	UFUNCTION(BlueprintPure, Category = "Save") static bool DoesSlotExist(const FString& Slot);
	static FString SlotPath(const FString& Slot);

	// ---- Events ----

	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnDialogueLine OnDialogueLine;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnDialogueEnded OnDialogueEnded;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnStoryEvent OnStoryEvent;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnTimeOfDayChanged OnTimeOfDayChanged;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnNotify OnNotify;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnQuestChanged OnQuestChanged;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnJournalAdded OnJournalAdded;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnFlagChanged OnFlagChanged;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnSfx OnSfx;
	UPROPERTY(BlueprintAssignable, Category = "Story") FLSOnChapterChanged OnChapterChanged;

	/** Problems found while loading or running data (also logged). Tests assert this stays empty. */
	TArray<FString> Problems;

private:
	void Report(const FString& Problem);
	void TryAutoComplete(FName Quest);
	void ShowNextLine();
	bool Tick(float DeltaTime);

	FLSNarrativeDatabase Database;
	FLSStorySaveData State;

	FName ActiveConversation;
	int32 LineIndex = INDEX_NONE;

	FTSTicker::FDelegateHandle TickHandle;
};

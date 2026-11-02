// The Last Skyfarer: narrative data types (dialogue, quests, journal, items, story state).
// Data is loaded from JSON in Content/LastSkyfarer/Data (see Unreal/Tools/convert_godot_data.py).

#pragma once

#include "CoreMinimal.h"
#include "LSNarrativeTypes.generated.h"

UENUM(BlueprintType)
enum class ELSActionType : uint8
{
	SetFlag,
	ClearFlag,
	GiveItem,
	TakeItem,
	StartQuest,
	AdvanceObjective,	// Arg = "quest_id:objective_id"
	CompleteQuest,
	AddJournal,
	Event,				// fires StoryEvents.json actions, then OnStoryEvent
	TimeOfDay,			// Arg = Morning | Sunset | Night | Dawn
	Chapter,			// Amount = chapter number
	Autosave,
	Sfx
};

UENUM(BlueprintType)
enum class ELSQuestState : uint8
{
	None,
	Active,
	Complete
};

USTRUCT(BlueprintType)
struct FLSStoryAction
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	ELSActionType Type = ELSActionType::SetFlag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FString Arg;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	int32 Amount = 1;
};

USTRUCT(BlueprintType)
struct FLSDialogueLine
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FName Speaker;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FName Emotion;

	/** Empty for action-only steps, which run their actions and are skipped. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FText Text;

	/** Established line: must stay word for word (checked by tests). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	bool bCanon = false;

	/** Key of the voice file, "conversation.NN". Empty for narrator lines. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FString VoiceKey;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	TArray<FLSStoryAction> Actions;
};

USTRUCT(BlueprintType)
struct FLSConversation
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FString Source;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	TArray<FLSDialogueLine> Lines;
};

USTRUCT(BlueprintType)
struct FLSObjectiveDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	FText Text;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	int32 Count = 1;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	bool bOptional = false;

	/** Conditions (AND) that must hold before the objective is shown. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	TArray<FString> HiddenUntil;
};

USTRUCT(BlueprintType)
struct FLSQuestDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	FText Title;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	int32 Chapter = 1;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	bool bMain = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	FText Description;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	bool bAutoComplete = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	FText TurnIn;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	TArray<FName> Rewards;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Quest")
	TArray<FLSObjectiveDef> Objectives;
};

USTRUCT(BlueprintType)
struct FLSJournalDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	FText Title;

	/** story | elias | piko */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	FName Kind;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	FName Collectible;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	bool bCanon = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	FText Text;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Journal")
	FString Source;
};

USTRUCT(BlueprintType)
struct FLSItemDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Item")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Item")
	FText Name;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Item")
	FName Category;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Item")
	FText Description;
};

USTRUCT(BlueprintType)
struct FLSSpeakerDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FText DisplayName;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FName Portrait;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FName DefaultEmotion;

	/** Subtitle colour, "#rrggbb". */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dialogue")
	FString Color;
};

USTRUCT(BlueprintType)
struct FLSLocationDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "World")
	FName Id;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "World")
	FText Name;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "World")
	FText Subtitle;
};

USTRUCT()
struct FLSStoryEventDef
{
	GENERATED_BODY()

	UPROPERTY()
	FName Id;

	UPROPERTY()
	TArray<FLSStoryAction> Actions;
};

USTRUCT()
struct FLSCollectibleObjective
{
	GENERATED_BODY()

	UPROPERTY()
	FName Group;

	/** "quest_id:objective_id" advanced when an entry of the group is added. */
	UPROPERTY()
	FString Objective;
};

// ---- JSON file wrappers (one per file in Content/LastSkyfarer/Data) ----

USTRUCT()
struct FLSConversationFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSConversation> Conversations;
};
USTRUCT()
struct FLSQuestFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSQuestDef> Quests;
};
USTRUCT()
struct FLSJournalFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSJournalDef> Entries;
};
USTRUCT()
struct FLSItemFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSItemDef> Items;
};
USTRUCT()
struct FLSSpeakerFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSSpeakerDef> Speakers;
};
USTRUCT()
struct FLSLocationFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSLocationDef> Locations;
};
USTRUCT()
struct FLSStoryEventFile
{
	GENERATED_BODY()

	UPROPERTY()
	TArray<FLSStoryEventDef> Events;

	UPROPERTY()
	TArray<FLSCollectibleObjective> CollectibleObjectives;
};

/** All narrative data, keyed by id. */
USTRUCT()
struct LASTSKYFARER_API FLSNarrativeDatabase
{
	GENERATED_BODY()

	UPROPERTY() TMap<FName, FLSConversation> Conversations;
	UPROPERTY() TMap<FName, FLSQuestDef> Quests;
	UPROPERTY() TMap<FName, FLSJournalDef> Journal;
	UPROPERTY() TMap<FName, FLSItemDef> Items;
	UPROPERTY() TMap<FName, FLSSpeakerDef> Speakers;
	UPROPERTY() TMap<FName, FLSLocationDef> Locations;
	UPROPERTY() TMap<FName, FLSStoryEventDef> Events;
	UPROPERTY() TMap<FName, FString> CollectibleObjectives;

	/** Default data folder: <ProjectContent>/LastSkyfarer/Data. */
	static FString DefaultDataDir();

	/** Loads every JSON file. Returns false and fills OutErrors if a file is missing or malformed. */
	bool LoadFromDirectory(const FString& Dir, TArray<FString>& OutErrors);

	/** Reference checks: speakers, quests, objectives, items, journal entries, events. */
	TArray<FString> Validate() const;

	const FLSObjectiveDef* FindObjective(FName QuestId, FName ObjectiveId) const;
};

USTRUCT(BlueprintType)
struct FLSQuestProgress
{
	GENERATED_BODY()

	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Quest")
	ELSQuestState State = ELSQuestState::None;

	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Quest")
	TMap<FName, int32> Objectives;
};

/** Everything the story remembers. Saved as-is. */
USTRUCT(BlueprintType)
struct FLSStorySaveData
{
	GENERATED_BODY()

	static constexpr int32 CurrentVersion = 1;

	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") int32 Version = CurrentVersion;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") TArray<FName> Flags;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") TMap<FName, int32> Inventory;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") TMap<FName, FLSQuestProgress> Quests;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") FName TrackedQuest;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") TArray<FName> Journal;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") TArray<FName> Discovered;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") FName TimeOfDay = TEXT("Morning");
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") int32 Chapter = 1;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") float PlaytimeSeconds = 0.f;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") FName MapName;
	UPROPERTY(SaveGame, BlueprintReadOnly, Category = "Save") FTransform PlayerTransform;
};

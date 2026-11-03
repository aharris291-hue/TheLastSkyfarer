// The Last Skyfarer: anything Kieran can talk to, inspect or pick up.
// Port of the Godot demo's Interactable: the first rule whose conditions pass is used.

#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "LSNarrativeTypes.h"
#include "LSInteractableComponent.generated.h"

class ULSStorySubsystem;

USTRUCT(BlueprintType)
struct FLSInteractionRule
{
	GENERATED_BODY()

	/** Conditions that must all pass (see ULSStorySubsystem::Check). Empty = always. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	TArray<FString> If;

	/** Conversation to play, or None. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	FName Conversation;

	/** Actions run after the conversation ends (or at once if there is none). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	TArray<FLSStoryAction> Do;

	/** A repeat line: still usable, but the "new" marker is not shown. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	bool bRepeat = false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FLSOnInteracted, AActor*, By);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FLSOnInteractableRefresh);

UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API ULSInteractableComponent : public USceneComponent
{
	GENERATED_BODY()

public:
	ULSInteractableComponent();

	/** Verb shown in the prompt: Talk, Inspect, Pick up, Open. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	FText Prompt;

	/** Kieran must be within this distance of the component, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	float Radius = 200.f;

	/** Conditions for the interactable to exist at all. Empty = always. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	TArray<FString> AvailableIf;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	TArray<FLSInteractionRule> Rules;

	UPROPERTY(BlueprintAssignable, Category = "Interaction")
	FLSOnInteracted OnInteracted;

	/** Story state changed: refresh markers (bound by the HUD or the owner). */
	UPROPERTY(BlueprintAssignable, Category = "Interaction")
	FLSOnInteractableRefresh OnRefresh;

	// Pure logic, testable without a world.
	static int32 PickRuleIndex(const TArray<FLSInteractionRule>& Rules, const ULSStorySubsystem& Story);
	bool CanInteractWith(const ULSStorySubsystem& Story) const;
	bool HasNewContentFor(const ULSStorySubsystem& Story) const;
	/** Plays the rule's conversation and queues its actions. Returns false if no rule applies. */
	bool InteractWith(ULSStorySubsystem& Story, AActor* By);

	UFUNCTION(BlueprintPure, Category = "Interaction") bool CanInteract() const;
	/** True when the rule that would fire is not a repeat: show the "!" marker. */
	UFUNCTION(BlueprintPure, Category = "Interaction") bool HasNewContent() const;
	UFUNCTION(BlueprintCallable, Category = "Interaction") bool Interact(AActor* By);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	UFUNCTION() void HandleDialogueEnded(FName ConversationId);
	UFUNCTION() void HandleFlagChanged(FName Flag, bool bSet);
	UFUNCTION() void HandleQuestChanged(FName Quest, ELSQuestState State);

	TWeakObjectPtr<ULSStorySubsystem> PendingStory;
	FName PendingConversation;
	TArray<FLSStoryAction> PendingActions;
};

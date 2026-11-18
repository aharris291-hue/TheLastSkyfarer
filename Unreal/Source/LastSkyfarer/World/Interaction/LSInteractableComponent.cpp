#include "LSInteractableComponent.h"

#include "LSInteractionSubsystem.h"
#include "LSStorySubsystem.h"
#include "Engine/World.h"

ULSInteractableComponent::ULSInteractableComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
	Prompt = NSLOCTEXT("LS", "Inspect", "Inspect");
}

void ULSInteractableComponent::BeginPlay()
{
	Super::BeginPlay();
	if (ULSInteractionSubsystem* Interactions = GetWorld()->GetSubsystem<ULSInteractionSubsystem>())
	{
		Interactions->Register(this);
	}
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnFlagChanged.AddDynamic(this, &ULSInteractableComponent::HandleFlagChanged);
		Story->OnQuestChanged.AddDynamic(this, &ULSInteractableComponent::HandleQuestChanged);
	}
}

void ULSInteractableComponent::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UWorld* World = GetWorld())
	{
		if (ULSInteractionSubsystem* Interactions = World->GetSubsystem<ULSInteractionSubsystem>())
		{
			Interactions->Unregister(this);
		}
	}
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnFlagChanged.RemoveAll(this);
		Story->OnQuestChanged.RemoveAll(this);
		Story->OnDialogueEnded.RemoveAll(this);
	}
	Super::EndPlay(Reason);
}

int32 ULSInteractableComponent::PickRuleIndex(const TArray<FLSInteractionRule>& InRules, const ULSStorySubsystem& Story)
{
	for (int32 i = 0; i < InRules.Num(); ++i)
	{
		if (Story.CheckAll(InRules[i].If)) return i;
	}
	return INDEX_NONE;
}

bool ULSInteractableComponent::CanInteractWith(const ULSStorySubsystem& Story) const
{
	return Story.CheckAll(AvailableIf) && PickRuleIndex(Rules, Story) != INDEX_NONE;
}

bool ULSInteractableComponent::HasNewContentFor(const ULSStorySubsystem& Story) const
{
	const int32 i = PickRuleIndex(Rules, Story);
	return Story.CheckAll(AvailableIf) && i != INDEX_NONE && !Rules[i].bRepeat;
}

bool ULSInteractableComponent::InteractWith(ULSStorySubsystem& Story, AActor* By)
{
	if (Story.IsInDialogue() || !CanInteractWith(Story)) return false;
	const FLSInteractionRule& Rule = Rules[PickRuleIndex(Rules, Story)];
	OnInteracted.Broadcast(By);

	if (!Rule.Conversation.IsNone() && Story.GetDatabase().Conversations.Contains(Rule.Conversation))
	{
		PendingStory = &Story;
		PendingConversation = Rule.Conversation;
		PendingActions = Rule.Do;
		Story.OnDialogueEnded.AddUniqueDynamic(this, &ULSInteractableComponent::HandleDialogueEnded);
		Story.StartConversation(Rule.Conversation);
	}
	else
	{
		Story.RunActions(Rule.Do);
		OnRefresh.Broadcast();
	}
	return true;
}

void ULSInteractableComponent::HandleDialogueEnded(FName ConversationId)
{
	if (ConversationId != PendingConversation) return;
	if (ULSStorySubsystem* Story = PendingStory.Get())
	{
		Story->OnDialogueEnded.RemoveDynamic(this, &ULSInteractableComponent::HandleDialogueEnded);
		const TArray<FLSStoryAction> Actions = MoveTemp(PendingActions);
		PendingConversation = NAME_None;
		PendingActions.Reset();
		Story->RunActions(Actions);
	}
	OnRefresh.Broadcast();
}

void ULSInteractableComponent::HandleFlagChanged(FName, bool) { OnRefresh.Broadcast(); }
void ULSInteractableComponent::HandleQuestChanged(FName, ELSQuestState) { OnRefresh.Broadcast(); }

bool ULSInteractableComponent::CanInteract() const
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	return Story && CanInteractWith(*Story);
}

bool ULSInteractableComponent::HasNewContent() const
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	return Story && HasNewContentFor(*Story);
}

bool ULSInteractableComponent::Interact(AActor* By)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	return Story && InteractWith(*Story, By);
}

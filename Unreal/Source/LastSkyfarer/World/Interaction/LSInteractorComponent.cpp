#include "LSInteractorComponent.h"

#include "LSInteractableComponent.h"
#include "LSInteractionSubsystem.h"
#include "LSStorySubsystem.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

ULSInteractorComponent::ULSInteractorComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

FText ULSInteractorComponent::GetPrompt() const
{
	const ULSInteractableComponent* T = Target.Get();
	return T ? T->Prompt : FText::GetEmpty();
}

void ULSInteractorComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	SearchTimer -= DeltaTime;
	if (SearchTimer <= 0.f)
	{
		SearchTimer = SearchInterval;
		RefreshTarget();
	}
}

void ULSInteractorComponent::RefreshTarget()
{
	ULSInteractableComponent* NewTarget = nullptr;
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	const ULSInteractionSubsystem* Interactions = GetWorld() ? GetWorld()->GetSubsystem<ULSInteractionSubsystem>() : nullptr;
	const AActor* Owner = GetOwner();
	if (Story && Interactions && Owner && !Story->IsInDialogue())
	{
		NewTarget = Interactions->FindBest(Owner->GetActorLocation(), Owner->GetActorForwardVector(), *Story);
	}
	if (NewTarget != Target.Get())
	{
		Target = NewTarget;
		OnTargetChanged.Broadcast(NewTarget, GetPrompt());
	}
}

bool ULSInteractorComponent::Interact()
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story) return false;
	if (Story->IsInDialogue())
	{
		Story->AdvanceDialogue();
		return true;
	}
	RefreshTarget();
	ULSInteractableComponent* T = Target.Get();
	const bool bUsed = T && T->InteractWith(*Story, GetOwner());
	RefreshTarget();
	return bUsed;
}

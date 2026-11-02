// The Last Skyfarer: HUD actor.

#include "LSHUD.h"

#include "GameFramework/PlayerController.h"
#include "LSHUDWidget.h"
#include "LSInteractorComponent.h"
#include "LSJournalWidget.h"
#include "LSPauseWidget.h"
#include "LSStorySubsystem.h"

void ALSHUD::BeginPlay()
{
	Super::BeginPlay();
	APlayerController* PC = GetOwningPlayerController();
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);

	HUDWidget = CreateWidget<ULSHUDWidget>(PC, ULSHUDWidget::StaticClass());
	HUDWidget->AddToViewport(0);
	HUDWidget->BindStory(Story);
	HUDWidget->OnAdvanceClicked.AddUObject(this, &ALSHUD::AdvanceDialogue);

	JournalWidget = CreateWidget<ULSJournalWidget>(PC, ULSJournalWidget::StaticClass());
	JournalWidget->SetStory(Story);
	JournalWidget->AddToViewport(10);
	JournalWidget->SetVisibility(ESlateVisibility::Collapsed);

	PauseWidget = CreateWidget<ULSPauseWidget>(PC, ULSPauseWidget::StaticClass());
	PauseWidget->SetStory(Story);
	PauseWidget->AddToViewport(20);
	PauseWidget->SetVisibility(ESlateVisibility::Collapsed);
	PauseWidget->OnResume.AddUObject(this, &ALSHUD::TogglePause);

	if (Story)
	{
		Story->OnDialogueLine.AddUniqueDynamic(this, &ALSHUD::HandleDialogueLine);
		Story->OnDialogueEnded.AddUniqueDynamic(this, &ALSHUD::HandleDialogueEnded);
	}
}

void ALSHUD::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// The pawn may be possessed after BeginPlay; bind its interactor when it appears.
	const APlayerController* PC = GetOwningPlayerController();
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	ULSInteractorComponent* Interactor = Pawn ? Pawn->FindComponentByClass<ULSInteractorComponent>() : nullptr;
	if (Interactor != BoundInteractor.Get())
	{
		if (ULSInteractorComponent* Old = BoundInteractor.Get())
		{
			Old->OnTargetChanged.RemoveDynamic(this, &ALSHUD::HandleTargetChanged);
		}
		BoundInteractor = Interactor;
		if (Interactor)
		{
			Interactor->OnTargetChanged.AddUniqueDynamic(this, &ALSHUD::HandleTargetChanged);
			HUDWidget->SetPrompt(Interactor->GetPrompt());
		}
	}
}

void ALSHUD::HandleTargetChanged(ULSInteractableComponent* Target, FText Prompt)
{
	HUDWidget->SetPrompt(Prompt);
}

void ALSHUD::HandleDialogueLine(FName ConversationId, const FLSDialogueLine& Line)
{
	UpdateInputMode();
}

void ALSHUD::HandleDialogueEnded(FName ConversationId)
{
	UpdateInputMode();
	if (const ULSInteractorComponent* Interactor = BoundInteractor.Get())
	{
		HUDWidget->SetPrompt(Interactor->GetPrompt());
	}
}

void ALSHUD::AdvanceDialogue()
{
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->AdvanceDialogue();
	}
}

void ALSHUD::ToggleJournal()
{
	if (bPauseOpen)
	{
		return;
	}
	bJournalOpen = !bJournalOpen;
	JournalWidget->SetVisibility(bJournalOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
	HUDWidget->SetVisibility(bJournalOpen ? ESlateVisibility::Collapsed : ESlateVisibility::SelfHitTestInvisible);
	if (bJournalOpen)
	{
		JournalWidget->ShowTab(JournalWidget->GetTab());
	}
	UpdateInputMode();
}

void ALSHUD::TogglePause()
{
	if (bJournalOpen)
	{
		ToggleJournal(); // Esc closes the journal first
		return;
	}
	bPauseOpen = !bPauseOpen;
	PauseWidget->SetVisibility(bPauseOpen ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
	UpdateInputMode();
}

void ALSHUD::PeekTracker()
{
	HUDWidget->RefreshTracker();
}

void ALSHUD::UpdateInputMode()
{
	APlayerController* PC = GetOwningPlayerController();
	if (!PC)
	{
		return;
	}
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	const bool bInDialogue = Story && Story->IsInDialogue();
	const bool bMenu = bJournalOpen || bPauseOpen;
	PC->SetPause(bMenu);
	PC->SetShowMouseCursor(bMenu || bInDialogue);
	PC->SetIgnoreMoveInput(bMenu || bInDialogue);
	if (bMenu || bInDialogue)
	{
		FInputModeGameAndUI Mode;
		Mode.SetHideCursorDuringCapture(false);
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		PC->SetInputMode(Mode);
	}
	else
	{
		PC->SetInputMode(FInputModeGameOnly());
		PC->ResetIgnoreMoveInput();
	}
}

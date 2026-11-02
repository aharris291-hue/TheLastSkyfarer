// The Last Skyfarer: pause menu.

#include "LSPauseWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetSystemLibrary.h"
#include "LSStorySubsystem.h"
#include "LSUIHelpers.h"

#define LOCTEXT_NAMESPACE "LSPause"

TSharedRef<SWidget> ULSPauseWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
		WidgetTree->RootWidget = Canvas;

		UBorder* Panel = WidgetTree->ConstructWidget<UBorder>();
		Panel->SetBrushColor(FLinearColor(0.04f, 0.035f, 0.03f, 0.92f));
		Panel->SetPadding(FMargin(40.f, 30.f));
		UCanvasPanelSlot* PanelSlot = Canvas->AddChildToCanvas(Panel);
		PanelSlot->SetAnchors(FAnchors(0.5f, 0.5f));
		PanelSlot->SetAlignment(FVector2D(0.5f, 0.5f));
		PanelSlot->SetAutoSize(true);

		UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>();
		Panel->SetContent(Column);
		Column->AddChildToVerticalBox(LSUI::MakeText(WidgetTree, LOCTEXT("Paused", "Paused"), 34, LSUI::Brass, true))->SetHorizontalAlignment(HAlign_Center);

		struct FEntry { FText Label; void (ULSPauseWidget::*Handler)(); };
		const FEntry Entries[] = {
			{ LOCTEXT("Resume", "Resume"), &ULSPauseWidget::HandleResume },
			{ LOCTEXT("Save", "Save game"), &ULSPauseWidget::HandleSave },
			{ LOCTEXT("Load", "Load game"), &ULSPauseWidget::HandleLoad },
			{ LOCTEXT("Quit", "Quit to desktop"), &ULSPauseWidget::HandleQuit },
		};
		for (const FEntry& E : Entries)
		{
			UButton* B = WidgetTree->ConstructWidget<UButton>();
			FButtonStyle Style = B->GetStyle();
			Style.Normal.TintColor = FSlateColor(FLinearColor(0.12f, 0.1f, 0.08f, 1.f));
			Style.Hovered.TintColor = FSlateColor(FLinearColor(0.25f, 0.2f, 0.12f, 1.f));
			B->SetStyle(Style);
			UTextBlock* Label = LSUI::MakeText(WidgetTree, E.Label, 24);
			Label->SetAutoWrapText(false);
			B->AddChild(Label);
			UVerticalBoxSlot* S = Column->AddChildToVerticalBox(B);
			S->SetPadding(FMargin(0.f, 10.f, 0.f, 0.f));
			S->SetHorizontalAlignment(HAlign_Fill);
			if (E.Handler == &ULSPauseWidget::HandleResume) { B->OnClicked.AddDynamic(this, &ULSPauseWidget::HandleResume); }
			else if (E.Handler == &ULSPauseWidget::HandleSave) { B->OnClicked.AddDynamic(this, &ULSPauseWidget::HandleSave); }
			else if (E.Handler == &ULSPauseWidget::HandleLoad) { B->OnClicked.AddDynamic(this, &ULSPauseWidget::HandleLoad); }
			else { B->OnClicked.AddDynamic(this, &ULSPauseWidget::HandleQuit); }
		}
		StatusText = LSUI::MakeText(WidgetTree, FText::GetEmpty(), 18, LSUI::Dim);
		Column->AddChildToVerticalBox(StatusText)->SetPadding(FMargin(0.f, 14.f, 0.f, 0.f));
	}
	return Super::RebuildWidget();
}

void ULSPauseWidget::Save()
{
	ULSStorySubsystem* Story = StoryRef.Get();
	const bool bOk = Story && Story->SaveToSlot(SlotName);
	StatusText->SetText(bOk ? LOCTEXT("Saved", "Game saved.") : LOCTEXT("SaveFailed", "Could not save."));
	UE_LOG(LogTemp, Display, TEXT("LS_UI save %s"), bOk ? TEXT("ok") : TEXT("failed"));
}

void ULSPauseWidget::Load()
{
	ULSStorySubsystem* Story = StoryRef.Get();
	const bool bOk = Story && Story->LoadFromSlot(SlotName);
	StatusText->SetText(bOk ? LOCTEXT("Loaded", "Game loaded.") : LOCTEXT("LoadFailed", "No saved game found."));
	UE_LOG(LogTemp, Display, TEXT("LS_UI load %s"), bOk ? TEXT("ok") : TEXT("failed"));
}

void ULSPauseWidget::HandleResume() { OnResume.Broadcast(); }
void ULSPauseWidget::HandleSave() { Save(); }
void ULSPauseWidget::HandleLoad() { Load(); }

void ULSPauseWidget::HandleQuit()
{
	UKismetSystemLibrary::QuitGame(this, GetOwningPlayer(), EQuitPreference::Quit, false);
}

#undef LOCTEXT_NAMESPACE

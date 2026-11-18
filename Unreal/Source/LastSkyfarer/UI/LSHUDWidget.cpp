// The Last Skyfarer: in-game HUD.

#include "LSHUDWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "LSStorySubsystem.h"
#include "LSUIHelpers.h"

#define LOCTEXT_NAMESPACE "LSHUD"

namespace
{
	UCanvasPanelSlot* Place(UCanvasPanel* Canvas, UWidget* W, const FAnchors& Anchors, const FVector2D& Alignment, const FVector2D& Pos, const FVector2D& Size, bool bAutoSize)
	{
		UCanvasPanelSlot* S = Canvas->AddChildToCanvas(W);
		S->SetAnchors(Anchors);
		S->SetAlignment(Alignment);
		S->SetPosition(Pos);
		S->SetSize(Size);
		S->SetAutoSize(bAutoSize);
		return S;
	}

	UBorder* MakePanel(UWidgetTree* Tree, const FMargin& Padding)
	{
		UBorder* B = Tree->ConstructWidget<UBorder>();
		B->SetBrushColor(LSUI::PanelTint);
		B->SetPadding(Padding);
		return B;
	}
}

TSharedRef<SWidget> ULSHUDWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
		WidgetTree->RootWidget = Canvas;

		// Quest tracker, top left.
		UBorder* TrackerPanel = MakePanel(WidgetTree, FMargin(18.f, 12.f));
		TrackerBox = WidgetTree->ConstructWidget<UVerticalBox>();
		TrackerTitle = LSUI::MakeText(WidgetTree, FText::GetEmpty(), 22, LSUI::Brass, true);
		TrackerObjectives = WidgetTree->ConstructWidget<UVerticalBox>();
		TrackerBox->AddChildToVerticalBox(TrackerTitle);
		TrackerBox->AddChildToVerticalBox(TrackerObjectives)->SetPadding(FMargin(0.f, 6.f, 0.f, 0.f));
		TrackerPanel->SetContent(TrackerBox);
		Place(Canvas, TrackerPanel, FAnchors(0.f, 0.f), FVector2D(0.f, 0.f), FVector2D(40.f, 40.f), FVector2D(460.f, 10.f), true);
		TrackerPanel->SetRenderOpacity(0.f);

		// Toast, top centre.
		ToastPanel = MakePanel(WidgetTree, FMargin(24.f, 10.f));
		ToastText = LSUI::MakeText(WidgetTree, FText::GetEmpty(), 24, LSUI::Parchment, true);
		ToastText->SetAutoWrapText(false);
		ToastPanel->SetContent(ToastText);
		Place(Canvas, ToastPanel, FAnchors(0.5f, 0.f), FVector2D(0.5f, 0.f), FVector2D(0.f, 60.f), FVector2D(10.f, 10.f), true);
		ToastPanel->SetVisibility(ESlateVisibility::Collapsed);

		// Interaction prompt, lower centre.
		PromptPanel = MakePanel(WidgetTree, FMargin(18.f, 8.f));
		PromptText = LSUI::MakeText(WidgetTree, FText::GetEmpty(), 24);
		PromptText->SetAutoWrapText(false);
		PromptPanel->SetContent(PromptText);
		Place(Canvas, PromptPanel, FAnchors(0.5f, 1.f), FVector2D(0.5f, 1.f), FVector2D(0.f, -300.f), FVector2D(10.f, 10.f), true);
		PromptPanel->SetVisibility(ESlateVisibility::Collapsed);

		// Dialogue box, bottom. A button so it can be clicked to advance.
		DialogueButton = WidgetTree->ConstructWidget<UButton>();
		FButtonStyle Style = DialogueButton->GetStyle();
		for (FSlateBrush* Brush : { &Style.Normal, &Style.Hovered, &Style.Pressed })
		{
			Brush->TintColor = FSlateColor(LSUI::PanelTint);
			Brush->DrawAs = ESlateBrushDrawType::Box;
		}
		DialogueButton->SetStyle(Style);
		UVerticalBox* DialogueBox = WidgetTree->ConstructWidget<UVerticalBox>();
		SpeakerText = LSUI::MakeText(WidgetTree, FText::GetEmpty(), 26, LSUI::Brass, true);
		LineText = LSUI::MakeText(WidgetTree, FText::GetEmpty(), 28);
		UTextBlock* Hint = LSUI::MakeText(WidgetTree, LOCTEXT("Continue", "E / click to continue"), 16, LSUI::Dim);
		DialogueBox->AddChildToVerticalBox(SpeakerText);
		DialogueBox->AddChildToVerticalBox(LineText)->SetPadding(FMargin(0.f, 8.f, 0.f, 8.f));
		UVerticalBoxSlot* HintSlot = DialogueBox->AddChildToVerticalBox(Hint);
		HintSlot->SetHorizontalAlignment(HAlign_Right);
		if (UButtonSlot* BoxSlot = Cast<UButtonSlot>(DialogueButton->AddChild(DialogueBox)))
		{
			BoxSlot->SetHorizontalAlignment(HAlign_Fill);
			BoxSlot->SetVerticalAlignment(VAlign_Top);
			BoxSlot->SetPadding(FMargin(28.f, 18.f));
		}
		Place(Canvas, DialogueButton, FAnchors(0.5f, 1.f), FVector2D(0.5f, 1.f), FVector2D(0.f, -40.f), FVector2D(1100.f, 210.f), false);
		DialogueButton->SetVisibility(ESlateVisibility::Collapsed);
		DialogueButton->OnClicked.AddDynamic(this, &ULSHUDWidget::HandleDialogueClicked);
	}
	return Super::RebuildWidget();
}

void ULSHUDWidget::BindStory(ULSStorySubsystem* Story)
{
	if (!Story)
	{
		return;
	}
	StoryRef = Story;
	Story->OnDialogueLine.AddUniqueDynamic(this, &ULSHUDWidget::HandleLine);
	Story->OnDialogueEnded.AddUniqueDynamic(this, &ULSHUDWidget::HandleEnded);
	Story->OnNotify.AddUniqueDynamic(this, &ULSHUDWidget::HandleNotify);
	Story->OnQuestChanged.AddUniqueDynamic(this, &ULSHUDWidget::HandleQuestChanged);
	RefreshTracker();
}

void ULSHUDWidget::ShowToast(const FText& Message)
{
	if (!ToastPanel)
	{
		return;
	}
	ToastText->SetText(Message);
	ToastPanel->SetVisibility(ESlateVisibility::HitTestInvisible);
	ToastPanel->SetRenderOpacity(1.f);
	ToastTimer = ToastTime;
}

void ULSHUDWidget::SetPrompt(const FText& Prompt)
{
	if (!PromptPanel)
	{
		return;
	}
	const bool bShow = !Prompt.IsEmpty() && !bDialogueOpen;
	PromptText->SetText(FText::Format(LOCTEXT("PromptFmt", "[E]  {0}"), Prompt));
	PromptPanel->SetVisibility(bShow ? ESlateVisibility::HitTestInvisible : ESlateVisibility::Collapsed);
}

void ULSHUDWidget::ShowTracker()
{
	TrackerTimer = TrackerShowTime;
}

void ULSHUDWidget::RefreshTracker()
{
	const ULSStorySubsystem* Story = StoryRef.Get();
	if (!Story || !TrackerBox)
	{
		return;
	}
	TrackerObjectives->ClearChildren();
	const FName Quest = Story->GetTrackedQuest();
	const FLSQuestDef* Def = Quest.IsNone() ? nullptr : Story->GetDatabase().Quests.Find(Quest);
	if (!Def || Story->GetQuestState(Quest) != ELSQuestState::Active)
	{
		TrackerTitle->SetText(FText::GetEmpty());
		TrackerTimer = 0.f;
		return;
	}
	TrackerTitle->SetText(Def->Title);
	for (const FLSObjectiveDef& Obj : Story->GetVisibleObjectives(Quest))
	{
		const bool bDone = Story->IsObjectiveDone(Quest, Obj.Id);
		FText Line = Obj.Text;
		if (Obj.Count > 1)
		{
			Line = FText::Format(LOCTEXT("ObjCount", "{0} ({1}/{2})"), Obj.Text, Story->GetObjectiveProgress(Quest, Obj.Id), Obj.Count);
		}
		Line = FText::Format(bDone ? LOCTEXT("ObjDone", "✓  {0}") : LOCTEXT("ObjOpen", "◇  {0}"), Line);
		TrackerObjectives->AddChildToVerticalBox(LSUI::MakeText(WidgetTree, Line, 20, bDone ? LSUI::Dim : LSUI::Parchment));
	}
	ShowTracker();
}

FText ULSHUDWidget::GetDialogueText() const
{
	return LineText ? LineText->GetText() : FText::GetEmpty();
}

FText ULSHUDWidget::GetDialogueSpeaker() const
{
	return SpeakerText ? SpeakerText->GetText() : FText::GetEmpty();
}

void ULSHUDWidget::HandleLine(FName ConversationId, const FLSDialogueLine& Line)
{
	FText Name;
	FLinearColor Color = LSUI::Parchment;
	if (const ULSStorySubsystem* Story = StoryRef.Get())
	{
		if (const FLSSpeakerDef* Speaker = Story->GetDatabase().Speakers.Find(Line.Speaker))
		{
			Name = Speaker->DisplayName;
			Color = LSUI::ParseHex(Speaker->Color);
		}
	}
	SpeakerText->SetText(Name);
	SpeakerText->SetColorAndOpacity(FSlateColor(Color));
	SpeakerText->SetVisibility(Name.IsEmpty() ? ESlateVisibility::Collapsed : ESlateVisibility::HitTestInvisible);
	LineText->SetText(Line.Text);
	// Narrator lines read as stage directions.
	LineText->SetColorAndOpacity(FSlateColor(Name.IsEmpty() ? LSUI::Dim : LSUI::Parchment));
	DialogueButton->SetVisibility(ESlateVisibility::Visible);
	bDialogueOpen = true;
	PromptPanel->SetVisibility(ESlateVisibility::Collapsed);
	UE_LOG(LogTemp, Display, TEXT("LS_UI dialogue %s: [%s] %s"), *ConversationId.ToString(), *Name.ToString(), *Line.Text.ToString());
}

void ULSHUDWidget::HandleEnded(FName ConversationId)
{
	DialogueButton->SetVisibility(ESlateVisibility::Collapsed);
	bDialogueOpen = false;
	UE_LOG(LogTemp, Display, TEXT("LS_UI dialogue %s ended"), *ConversationId.ToString());
}

void ULSHUDWidget::HandleNotify(const FText& Message)
{
	ShowToast(Message);
	UE_LOG(LogTemp, Display, TEXT("LS_UI toast: %s"), *Message.ToString());
}

void ULSHUDWidget::HandleQuestChanged(FName QuestId, ELSQuestState State)
{
	RefreshTracker();
}

void ULSHUDWidget::HandleDialogueClicked()
{
	OnAdvanceClicked.Broadcast();
}

void ULSHUDWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	if (TrackerBox && TrackerBox->GetParent())
	{
		TrackerTimer = FMath::Max(0.f, TrackerTimer - InDeltaTime);
		const bool bHasQuest = !TrackerTitle->GetText().IsEmpty();
		const float Target = bHasQuest && TrackerTimer > 0.f ? 1.f : 0.f;
		UWidget* Panel = TrackerBox->GetParent();
		Panel->SetRenderOpacity(FMath::FInterpConstantTo(Panel->GetRenderOpacity(), Target, InDeltaTime, 2.f));
	}
	if (ToastTimer > 0.f)
	{
		ToastTimer -= InDeltaTime;
		if (ToastTimer < 0.5f)
		{
			ToastPanel->SetRenderOpacity(FMath::Max(0.f, ToastTimer / 0.5f));
		}
		if (ToastTimer <= 0.f)
		{
			ToastPanel->SetVisibility(ESlateVisibility::Collapsed);
		}
	}
}

#undef LOCTEXT_NAMESPACE

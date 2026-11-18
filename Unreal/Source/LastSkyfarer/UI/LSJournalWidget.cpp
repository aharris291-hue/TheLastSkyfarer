// The Last Skyfarer: journal screen with the four tabs from GDD 9.

#include "LSJournalWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/ScrollBox.h"
#include "Components/ScrollBoxSlot.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "LSStorySubsystem.h"
#include "LSUIHelpers.h"

#define LOCTEXT_NAMESPACE "LSJournal"

TSharedRef<SWidget> ULSJournalWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
		WidgetTree->RootWidget = Canvas;

		UBorder* Page = WidgetTree->ConstructWidget<UBorder>();
		Page->SetBrushColor(FLinearColor(0.05f, 0.04f, 0.03f, 1.f));
		Page->SetPadding(FMargin(36.f, 28.f));
		UCanvasPanelSlot* PageSlot = Canvas->AddChildToCanvas(Page);
		PageSlot->SetAnchors(FAnchors(0.1f, 0.08f, 0.9f, 0.92f));
		PageSlot->SetOffsets(FMargin(0.f));

		UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>();
		Page->SetContent(Column);
		Column->AddChildToVerticalBox(LSUI::MakeText(WidgetTree, LOCTEXT("Title", "Journal"), 34, LSUI::Brass, true));

		UHorizontalBox* Tabs = WidgetTree->ConstructWidget<UHorizontalBox>();
		Column->AddChildToVerticalBox(Tabs)->SetPadding(FMargin(0.f, 12.f, 0.f, 12.f));
		const FText Names[] = { LOCTEXT("TabQuests", "Quests"), LOCTEXT("TabDisc", "Discoveries"), LOCTEXT("TabElias", "Elias's Journal"), LOCTEXT("TabPiko", "Piko's Notes") };
		for (int32 i = 0; i < 4; ++i)
		{
			UButton* B = WidgetTree->ConstructWidget<UButton>();
			FButtonStyle Style = B->GetStyle();
			Style.Normal.TintColor = FSlateColor(FLinearColor(0.12f, 0.1f, 0.08f, 1.f));
			Style.Hovered.TintColor = FSlateColor(FLinearColor(0.22f, 0.18f, 0.12f, 1.f));
			Style.Pressed.TintColor = FSlateColor(FLinearColor(0.3f, 0.24f, 0.14f, 1.f));
			B->SetStyle(Style);
			UTextBlock* Label = LSUI::MakeText(WidgetTree, Names[i], 22);
			Label->SetAutoWrapText(false);
			B->AddChild(Label);
			Tabs->AddChildToHorizontalBox(B)->SetPadding(FMargin(0.f, 0.f, 10.f, 0.f));
			TabButtons.Add(B);
			TabLabels.Add(Label);
		}
		TabButtons[0]->OnClicked.AddDynamic(this, &ULSJournalWidget::OnQuestsTab);
		TabButtons[1]->OnClicked.AddDynamic(this, &ULSJournalWidget::OnDiscoveriesTab);
		TabButtons[2]->OnClicked.AddDynamic(this, &ULSJournalWidget::OnEliasTab);
		TabButtons[3]->OnClicked.AddDynamic(this, &ULSJournalWidget::OnPikoTab);

		Content = WidgetTree->ConstructWidget<UScrollBox>();
		UVerticalBoxSlot* ContentSlot = Column->AddChildToVerticalBox(Content);
		ContentSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

		UTextBlock* Hint = LSUI::MakeText(WidgetTree, LOCTEXT("Hint", "J or Esc to close"), 16, LSUI::Dim);
		Hint->SetAutoWrapText(false);
		Column->AddChildToVerticalBox(Hint)->SetHorizontalAlignment(HAlign_Right);
	}
	return Super::RebuildWidget();
}

void ULSJournalWidget::AddHeading(const FText& Text)
{
	Content->AddChild(LSUI::MakeText(WidgetTree, Text, 24, LSUI::Brass, true));
	Cast<UScrollBoxSlot>(Content->GetChildAt(Content->GetChildrenCount() - 1)->Slot)->SetPadding(FMargin(0.f, 14.f, 0.f, 4.f));
}

void ULSJournalWidget::AddBody(const FText& Text, bool bDim)
{
	Content->AddChild(LSUI::MakeText(WidgetTree, Text, 20, bDim ? LSUI::Dim : LSUI::Parchment));
}

void ULSJournalWidget::AddEmpty(const FText& Text)
{
	AddBody(Text, true);
}

void ULSJournalWidget::ShowTab(ELSJournalTab Tab)
{
	CurrentTab = Tab;
	EntryCount = 0;
	if (!Content)
	{
		return;
	}
	Content->ClearChildren();
	for (int32 i = 0; i < TabLabels.Num(); ++i)
	{
		TabLabels[i]->SetColorAndOpacity(FSlateColor(i == static_cast<int32>(Tab) ? LSUI::Brass : LSUI::Parchment));
	}
	switch (Tab)
	{
	case ELSJournalTab::Quests: FillQuests(); break;
	case ELSJournalTab::Discoveries: FillDiscoveries(); break;
	case ELSJournalTab::Elias: FillJournalKind(TEXT("elias"), LOCTEXT("NoElias", "No pages of Elias's journal found yet.")); break;
	case ELSJournalTab::Piko: FillJournalKind(TEXT("piko"), LOCTEXT("NoPiko", "Nothing written about Piko yet.")); break;
	}
	UE_LOG(LogTemp, Display, TEXT("LS_UI journal tab %d: %d entries"), static_cast<int32>(Tab), EntryCount);
}

void ULSJournalWidget::FillQuests()
{
	const ULSStorySubsystem* Story = StoryRef.Get();
	if (!Story)
	{
		return;
	}
	for (const ELSQuestState Wanted : { ELSQuestState::Active, ELSQuestState::Complete })
	{
		for (const TPair<FName, FLSQuestDef>& Pair : Story->GetDatabase().Quests)
		{
			if (Story->GetQuestState(Pair.Key) != Wanted)
			{
				continue;
			}
			++EntryCount;
			AddHeading(Wanted == ELSQuestState::Complete
				? FText::Format(LOCTEXT("QuestDone", "{0}  (complete)"), Pair.Value.Title) : Pair.Value.Title);
			AddBody(Pair.Value.Description, Wanted == ELSQuestState::Complete);
			if (Wanted == ELSQuestState::Active)
			{
				for (const FLSObjectiveDef& Obj : Story->GetVisibleObjectives(Pair.Key))
				{
					const bool bDone = Story->IsObjectiveDone(Pair.Key, Obj.Id);
					AddBody(FText::Format(bDone ? LOCTEXT("JObjDone", "   ✓  {0}") : LOCTEXT("JObjOpen", "   ◇  {0}"), Obj.Text), bDone);
				}
			}
		}
	}
	if (EntryCount == 0)
	{
		AddEmpty(LOCTEXT("NoQuests", "No quests yet."));
	}
}

void ULSJournalWidget::FillJournalKind(FName Kind, const FText& EmptyText)
{
	const ULSStorySubsystem* Story = StoryRef.Get();
	if (!Story)
	{
		return;
	}
	for (const FName Id : Story->GetState().Journal)
	{
		const FLSJournalDef* Def = Story->GetDatabase().Journal.Find(Id);
		if (Def && Def->Kind == Kind)
		{
			++EntryCount;
			AddHeading(Def->Title);
			AddBody(Def->Text);
		}
	}
	if (EntryCount == 0)
	{
		AddEmpty(EmptyText);
	}
}

void ULSJournalWidget::FillDiscoveries()
{
	const ULSStorySubsystem* Story = StoryRef.Get();
	if (!Story)
	{
		return;
	}
	// GDD 9: confirmed facts are kept apart from open questions. The data marks only confirmed
	// entries for now, so open questions appear once the writers add them.
	AddHeading(LOCTEXT("Confirmed", "Confirmed"));
	for (const FName Id : Story->GetState().Journal)
	{
		const FLSJournalDef* Def = Story->GetDatabase().Journal.Find(Id);
		if (Def && Def->Kind == TEXT("story"))
		{
			++EntryCount;
			AddBody(FText::Format(LOCTEXT("DiscEntry", "{0}: {1}"), Def->Title, Def->Text));
		}
	}
	for (const FName Id : Story->GetState().Discovered)
	{
		if (const FLSLocationDef* Loc = Story->GetDatabase().Locations.Find(Id))
		{
			++EntryCount;
			AddBody(FText::Format(LOCTEXT("PlaceEntry", "Place: {0} ({1})"), Loc->Name, Loc->Subtitle));
		}
	}
	if (EntryCount == 0)
	{
		AddEmpty(LOCTEXT("NoDisc", "Nothing discovered yet."));
	}
	AddHeading(LOCTEXT("Open", "Open questions"));
	AddEmpty(LOCTEXT("NoOpen", "None recorded yet."));
}

void ULSJournalWidget::OnQuestsTab() { ShowTab(ELSJournalTab::Quests); }
void ULSJournalWidget::OnDiscoveriesTab() { ShowTab(ELSJournalTab::Discoveries); }
void ULSJournalWidget::OnEliasTab() { ShowTab(ELSJournalTab::Elias); }
void ULSJournalWidget::OnPikoTab() { ShowTab(ELSJournalTab::Piko); }

#undef LOCTEXT_NAMESPACE

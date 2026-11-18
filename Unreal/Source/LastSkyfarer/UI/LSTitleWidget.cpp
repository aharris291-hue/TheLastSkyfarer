// The Last Skyfarer: title screen.

#include "LSTitleWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "LSMenu.h"
#include "LSSettingsWidget.h"
#include "LSStorySubsystem.h"
#include "LSUIHelpers.h"

#define LOCTEXT_NAMESPACE "LSTitle"

const TCHAR* ULSTitleWidget::BrindleMap = TEXT("/Game/LastSkyfarer/Maps/Brindle/L_Brindle");
const TCHAR* ULSTitleWidget::TitleMap = TEXT("/Game/LastSkyfarer/Maps/Title/L_Title");

FString ULSTitleWidget::NewestSlot()
{
	FString Best;
	FDateTime BestTime = FDateTime::MinValue();
	for (const TCHAR* SlotName : { TEXT("autosave"), TEXT("slot1") })
	{
		if (ULSStorySubsystem::DoesSlotExist(SlotName))
		{
			const FDateTime T = IFileManager::Get().GetTimeStamp(*ULSStorySubsystem::SlotPath(SlotName));
			if (Best.IsEmpty() || T > BestTime)
			{
				Best = SlotName;
				BestTime = T;
			}
		}
	}
	return Best;
}

TSharedRef<SWidget> ULSTitleWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
		WidgetTree->RootWidget = Canvas;

		MainColumn = WidgetTree->ConstructWidget<UVerticalBox>();
		UCanvasPanelSlot* ColumnSlot = Canvas->AddChildToCanvas(MainColumn);
		ColumnSlot->SetAnchors(FAnchors(0.08f, 0.5f));
		ColumnSlot->SetAlignment(FVector2D(0.f, 0.5f));
		ColumnSlot->SetAutoSize(true);

		MainColumn->AddChildToVerticalBox(LSUI::MakeText(WidgetTree, LOCTEXT("Title", "THE LAST SKYFARER"), 60, LSUI::Brass, true));
		MainColumn->AddChildToVerticalBox(LSUI::MakeText(WidgetTree, LOCTEXT("Sub", "Windrest demo  (Milestone A greybox)"), 20, LSUI::Dim))
			->SetPadding(FMargin(4.f, 0.f, 0.f, 30.f));

		auto AddButton = [this](const FText& Label, TFunction<void()> Fn)
		{
			UButton* B = LSUI::MakeMenuButton(WidgetTree, Label, 28, this, Proxies, MoveTemp(Fn));
			UVerticalBoxSlot* S = MainColumn->AddChildToVerticalBox(B);
			S->SetPadding(FMargin(0.f, 8.f, 0.f, 0.f));
			S->SetHorizontalAlignment(HAlign_Left);
			return B;
		};
		FirstButton = AddButton(LOCTEXT("New", "New Game"), [this]() { NewGame(); });
		ContinueButton = AddButton(LOCTEXT("Continue", "Continue"), [this]() { Continue(); });
		AddButton(LOCTEXT("Settings", "Settings"), [this]() { ShowSettings(true); });
		AddButton(LOCTEXT("Quit", "Quit"), [this]() { UKismetSystemLibrary::QuitGame(this, GetOwningPlayer(), EQuitPreference::Quit, false); });

		Settings = CreateWidget<ULSSettingsWidget>(this, ULSSettingsWidget::StaticClass());
		Settings->OnBack.AddWeakLambda(this, [this]() { ShowSettings(false); });
		UCanvasPanelSlot* SettingsSlot = Canvas->AddChildToCanvas(Settings);
		SettingsSlot->SetAnchors(FAnchors(0.5f, 0.5f));
		SettingsSlot->SetAlignment(FVector2D(0.5f, 0.5f));
		SettingsSlot->SetAutoSize(true);
		Settings->SetVisibility(ESlateVisibility::Collapsed);
	}
	return Super::RebuildWidget();
}

void ULSTitleWidget::NativeConstruct()
{
	Super::NativeConstruct();
	ContinueButton->SetIsEnabled(CanContinue());
	FocusFirst();
}

void ULSTitleWidget::FocusFirst()
{
	(ContinueButton && ContinueButton->GetIsEnabled() ? ContinueButton : FirstButton)->SetKeyboardFocus();
}

void ULSTitleWidget::ShowSettings(bool bShow)
{
	MainColumn->SetVisibility(bShow ? ESlateVisibility::Collapsed : ESlateVisibility::Visible);
	Settings->SetVisibility(bShow ? ESlateVisibility::Visible : ESlateVisibility::Collapsed);
	if (bShow)
	{
		Settings->FocusFirst();
	}
	else
	{
		FocusFirst();
	}
}

void ULSTitleWidget::NewGame()
{
	UE_LOG(LogTemp, Display, TEXT("LS_TITLE new game"));
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->NewGame();
	}
	UGameplayStatics::OpenLevel(this, FName(BrindleMap));
}

bool ULSTitleWidget::Continue()
{
	const FString SaveSlot = NewestSlot();
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (SaveSlot.IsEmpty() || !Story || !Story->LoadFromSlot(SaveSlot))
	{
		UE_LOG(LogTemp, Display, TEXT("LS_TITLE continue: no save to load"));
		return false;
	}
	UE_LOG(LogTemp, Display, TEXT("LS_TITLE continue from %s"), *SaveSlot);
	// "Continue" tells Brindle Isle to put Kieran back where the save was made.
	UGameplayStatics::OpenLevel(this, FName(BrindleMap), true, TEXT("Continue"));
	return true;
}

#undef LOCTEXT_NAMESPACE

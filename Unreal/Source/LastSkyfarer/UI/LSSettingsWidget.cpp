// The Last Skyfarer: Settings panel.

#include "LSSettingsWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/SizeBox.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "LSMenu.h"
#include "LSSettings.h"
#include "LSUIHelpers.h"

#define LOCTEXT_NAMESPACE "LSSettings"

namespace
{
	struct FRow
	{
		FText Label;
		TFunction<FText()> Show;
		TFunction<void(int32)> Step; // -1 or +1
	};

	FText Percent(float V) { return FText::AsPercent(FMath::RoundToFloat(V * 10.f) / 10.f); }
	FText OnOff(bool b) { return b ? LOCTEXT("On", "On") : LOCTEXT("Off", "Off"); }
}

TSharedRef<SWidget> ULSSettingsWidget::RebuildWidget()
{
	if (WidgetTree && !WidgetTree->RootWidget)
	{
		ULSSettings* S = ULSSettings::Get();
		const TArray<FRow> Rows = {
			{ LOCTEXT("Master", "Master volume"), [S]() { return Percent(S->MasterVolume); }, [S](int32 D) { S->MasterVolume = FMath::Clamp(S->MasterVolume + D * 0.1f, 0.f, 1.f); } },
			{ LOCTEXT("Music", "Music volume"), [S]() { return Percent(S->MusicVolume); }, [S](int32 D) { S->MusicVolume = FMath::Clamp(S->MusicVolume + D * 0.1f, 0.f, 1.f); } },
			{ LOCTEXT("Effects", "Effects volume"), [S]() { return Percent(S->EffectsVolume); }, [S](int32 D) { S->EffectsVolume = FMath::Clamp(S->EffectsVolume + D * 0.1f, 0.f, 1.f); } },
			{ LOCTEXT("Look", "Look sensitivity"), [S]() { return FText::AsNumber(S->LookSensitivity); }, [S](int32 D) { S->LookSensitivity = FMath::Clamp(S->LookSensitivity + D * 0.25f, 0.25f, 3.f); } },
			{ LOCTEXT("Invert", "Invert Y"), [S]() { return OnOff(S->bInvertY); }, [S](int32) { S->bInvertY = !S->bInvertY; } },
			{ LOCTEXT("Subtitles", "Subtitles"), [S]() { return OnOff(S->bSubtitles); }, [S](int32) { S->bSubtitles = !S->bSubtitles; } },
		};

		UBorder* Panel = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Root"));
		Panel->SetBrushColor(FLinearColor(0.04f, 0.035f, 0.03f, 0.92f));
		Panel->SetPadding(FMargin(36.f, 26.f));
		WidgetTree->RootWidget = Panel;

		UVerticalBox* Column = WidgetTree->ConstructWidget<UVerticalBox>();
		Panel->SetContent(Column);
		Column->AddChildToVerticalBox(LSUI::MakeText(WidgetTree, LOCTEXT("Title", "Settings"), 30, LSUI::Brass, true));

		for (const FRow& R : Rows)
		{
			UHorizontalBox* Line = WidgetTree->ConstructWidget<UHorizontalBox>();
			USizeBox* LabelBox = WidgetTree->ConstructWidget<USizeBox>();
			LabelBox->SetWidthOverride(260.f);
			LabelBox->SetContent(LSUI::MakeText(WidgetTree, R.Label, 22));
			Line->AddChildToHorizontalBox(LabelBox)->SetVerticalAlignment(VAlign_Center);

			UButton* Less = LSUI::MakeMenuButton(WidgetTree, FText::FromString(TEXT("<")), 22, this, Proxies, [this, R]() { R.Step(-1); ULSSettings::Get()->SaveAndApply(this); Refresh(); });
			Line->AddChildToHorizontalBox(Less);
			USizeBox* ValueBox = WidgetTree->ConstructWidget<USizeBox>();
			ValueBox->SetWidthOverride(110.f);
			UTextBlock* Value = LSUI::MakeText(WidgetTree, R.Show(), 22);
			Value->SetJustification(ETextJustify::Center);
			ValueBox->SetContent(Value);
			Values.Add(Value);
			Line->AddChildToHorizontalBox(ValueBox)->SetVerticalAlignment(VAlign_Center);
			Line->AddChildToHorizontalBox(LSUI::MakeMenuButton(WidgetTree, FText::FromString(TEXT(">")), 22, this, Proxies, [this, R]() { R.Step(1); ULSSettings::Get()->SaveAndApply(this); Refresh(); }));
			Column->AddChildToVerticalBox(Line)->SetPadding(FMargin(0.f, 10.f, 0.f, 0.f));
			if (!FirstButton)
			{
				FirstButton = Less;
			}
		}
		Column->AddChildToVerticalBox(LSUI::MakeText(WidgetTree,
			LOCTEXT("Note", "Music, effects and subtitles take effect once audio and voices are in the game."), 16, LSUI::Dim))->SetPadding(FMargin(0.f, 14.f, 0.f, 0.f));
		Column->AddChildToVerticalBox(LSUI::MakeMenuButton(WidgetTree, LOCTEXT("Back", "Back"), 24, this, Proxies, [this]() { OnBack.Broadcast(); }))
			->SetPadding(FMargin(0.f, 18.f, 0.f, 0.f));

		// Refresh reads the values in the same order as Rows.
		RowShows.Reset();
		for (const FRow& R : Rows)
		{
			RowShows.Add(R.Show);
		}
	}
	return Super::RebuildWidget();
}

void ULSSettingsWidget::Refresh()
{
	for (int32 i = 0; i < Values.Num() && i < RowShows.Num(); ++i)
	{
		Values[i]->SetText(RowShows[i]());
	}
}

void ULSSettingsWidget::FocusFirst()
{
	if (FirstButton)
	{
		FirstButton->SetKeyboardFocus();
	}
}

#undef LOCTEXT_NAMESPACE

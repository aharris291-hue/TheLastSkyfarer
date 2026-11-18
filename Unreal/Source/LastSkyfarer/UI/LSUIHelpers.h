// The Last Skyfarer: shared helpers and placeholder style for the code-built UMG widgets.
// Placeholder look: dark translucent panels with parchment text. The parchment/ink/brass look from
// STYLE_GUIDE section 6 replaces these colours and brushes later.

#pragma once

#include "CoreMinimal.h"
#include "Components/TextBlock.h"
#include "Blueprint/WidgetTree.h"
#include "Fonts/SlateFontInfo.h"
#include "Styling/CoreStyle.h"

namespace LSUI
{
	inline const FLinearColor Parchment = FLinearColor::FromSRGBColor(FColor(0xE9, 0xE1, 0xCC));
	inline const FLinearColor Brass = FLinearColor::FromSRGBColor(FColor(0xC7, 0x9A, 0x3B));
	inline const FLinearColor Ink = FLinearColor::FromSRGBColor(FColor(0x1E, 0x1A, 0x16));
	inline const FLinearColor PanelTint = FLinearColor(0.03f, 0.025f, 0.02f, 0.78f);
	inline const FLinearColor Dim = FLinearColor(0.75f, 0.72f, 0.65f, 1.f);

	inline UTextBlock* MakeText(UWidgetTree* Tree, const FText& Text, int32 Size, const FLinearColor& Color = Parchment, bool bBold = false)
	{
		UTextBlock* T = Tree->ConstructWidget<UTextBlock>();
		T->SetText(Text);
		FSlateFontInfo Font = FCoreStyle::GetDefaultFontStyle(bBold ? "Bold" : "Regular", Size);
		T->SetFont(Font);
		T->SetColorAndOpacity(FSlateColor(Color));
		T->SetAutoWrapText(true);
		return T;
	}

	/** "#rrggbb" to a colour; falls back to parchment. */
	inline FLinearColor ParseHex(const FString& Hex)
	{
		return Hex.StartsWith(TEXT("#")) && Hex.Len() == 7 ? FLinearColor::FromSRGBColor(FColor::FromHex(Hex)) : Parchment;
	}
}

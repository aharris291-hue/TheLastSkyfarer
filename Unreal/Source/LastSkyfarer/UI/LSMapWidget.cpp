// The Last Skyfarer: map screen.

#include "LSMapWidget.h"

#include "Engine/TextureRenderTarget2D.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "LSMapBounds.h"
#include "LSMapMarkerComponent.h"
#include "LSStorySubsystem.h"
#include "LSUIHelpers.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

#define LOCTEXT_NAMESPACE "LSMap"

namespace
{
	const FLinearColor ParchmentBg = FLinearColor::FromSRGBColor(FColor(0xD9, 0xC9, 0xA3));
	const FLinearColor InkColor = FLinearColor::FromSRGBColor(FColor(0x2B, 0x22, 0x18));
	const FLinearColor PencilColor = FLinearColor(0.35f, 0.33f, 0.3f, 0.8f);
	const FLinearColor PinColor = FLinearColor::FromSRGBColor(FColor(0x2E, 0x7D, 0x4F));
	const FLinearColor PlayerColor = FLinearColor::FromSRGBColor(FColor(0xB0, 0x2E, 0x26));
	const FLinearColor TravelColor = FLinearColor::FromSRGBColor(FColor(0x4B, 0xB3, 0xFF));
	constexpr float PinPickRadius = 18.f;

	TArray<FVector2f> Circle(const FVector2f& C, float R, int32 Steps = 20)
	{
		TArray<FVector2f> P;
		for (int32 i = 0; i <= Steps; ++i)
		{
			const float A = 2.f * PI * i / Steps;
			P.Add(C + FVector2f(FMath::Cos(A), FMath::Sin(A)) * R);
		}
		return P;
	}
}

void ULSMapWidget::Refresh()
{
	MapBounds = ALSMapBounds::Find(this);
	if (ALSMapBounds* B = MapBounds.Get())
	{
		B->CaptureNow();
		if (UTextureRenderTarget2D* Image = B->GetMapImage())
		{
			MapBrush.SetResourceObject(Image);
			MapBrush.ImageSize = FVector2D(Image->SizeX, Image->SizeY);
			MapBrush.DrawAs = ESlateBrushDrawType::Image;
		}
	}
	SetKeyboardFocus();
}

FSlateRect ULSMapWidget::MapRect(const FGeometry& Geometry) const
{
	const FVector2D Size = Geometry.GetLocalSize();
	const float Side = FMath::Min(Size.X, Size.Y) * 0.86f;
	const FVector2D TopLeft((Size.X - Side) * 0.5f, (Size.Y - Side) * 0.5f);
	return FSlateRect(TopLeft, TopLeft + FVector2D(Side, Side));
}

int32 ULSMapWidget::NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	LayerId = Super::NativePaint(Args, AllottedGeometry, MyCullingRect, OutDrawElements, LayerId, InWidgetStyle, bParentEnabled);
	const FSlateBrush* White = FCoreStyle::Get().GetBrush("WhiteBrush");
	const FVector2D Size = AllottedGeometry.GetLocalSize();
	const FSlateRect R = MapRect(AllottedGeometry);
	const FVector2f TL(R.Left, R.Top);
	const float Side = R.Right - R.Left;
	auto Box = [&](const FVector2f& Pos, const FVector2f& Sz)
	{
		return AllottedGeometry.ToPaintGeometry(Sz, FSlateLayoutTransform(Pos));
	};
	const FPaintGeometry Geo = AllottedGeometry.ToPaintGeometry();
	const FSlateFontInfo LabelFont = FCoreStyle::GetDefaultFontStyle("Bold", 14);
	const FSlateFontInfo SmallFont = FCoreStyle::GetDefaultFontStyle("Regular", 13);

	// Dim the game behind the map, then the parchment sheet.
	FSlateDrawElement::MakeBox(OutDrawElements, LayerId, Box(FVector2f(0.f, 0.f), FVector2f(Size)), White, ESlateDrawEffect::None, FLinearColor(0.f, 0.f, 0.f, 0.6f));
	FSlateDrawElement::MakeBox(OutDrawElements, LayerId + 1, Box(TL - FVector2f(14.f, 14.f), FVector2f(Side + 28.f, Side + 28.f)), White, ESlateDrawEffect::None, ParchmentBg);

	const ALSMapBounds* B = MapBounds.Get();
	if (B && MapBrush.GetResourceObject())
	{
		// The capture, tinted towards sepia so it reads as a drawn sheet.
		FSlateDrawElement::MakeBox(OutDrawElements, LayerId + 2, Box(TL, FVector2f(Side, Side)), &MapBrush, ESlateDrawEffect::None, FLinearColor(0.95f, 0.85f, 0.68f, 0.85f));
	}
	FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 3, Geo,
		TArray<FVector2f>{ TL, TL + FVector2f(Side, 0.f), TL + FVector2f(Side, Side), TL + FVector2f(0.f, Side), TL }, ESlateDrawEffect::None, InkColor, true, 3.f);

	const int32 L = LayerId + 4;
	DrawnMarkers = 0;
	if (!B)
	{
		FSlateDrawElement::MakeText(OutDrawElements, L, Box(TL + FVector2f(20.f, 20.f), FVector2f(400.f, 30.f)),
			LOCTEXT("NoMap", "No map for this place yet.").ToString(), LabelFont, ESlateDrawEffect::None, InkColor);
		return L + 1;
	}
	auto ToScreen = [&](const FVector& World)
	{
		const FVector2D M = B->WorldToMap(World);
		return TL + FVector2f(M.X, M.Y) * Side;
	};

	// Markers.
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	const ULSMapSubsystem* MapSys = GetWorld() ? GetWorld()->GetSubsystem<ULSMapSubsystem>() : nullptr;
	if (Story && MapSys)
	{
		for (const FLSMapMarkerView& M : MapSys->GetVisibleMarkers(*Story))
		{
			const FVector2f P = ToScreen(M.WorldLocation);
			++DrawnMarkers;
			switch (M.Kind)
			{
			case ELSMapMarkerKind::Landmark:
			{
				const bool bKnown = M.Knowledge == ELSMapKnowledge::Known;
				const FLinearColor Col = bKnown ? InkColor : PencilColor;
				FSlateDrawElement::MakeLines(OutDrawElements, L, Geo, Circle(P, 7.f), ESlateDrawEffect::None, Col, true, bKnown ? 3.f : 1.5f);
				const FString Label = bKnown ? M.Label.ToString() : M.Label.ToString() + TEXT(" ?");
				FSlateDrawElement::MakeText(OutDrawElements, L, Box(P + FVector2f(11.f, -10.f), FVector2f(260.f, 20.f)), Label,
					bKnown ? LabelFont : SmallFont, ESlateDrawEffect::None, Col);
				break;
			}
			case ELSMapMarkerKind::Objective:
			{
				const float S = M.bTracked ? 11.f : 7.f;
				const TArray<FVector2f> Diamond{ P + FVector2f(0.f, -S), P + FVector2f(S, 0.f), P + FVector2f(0.f, S), P + FVector2f(-S, 0.f), P + FVector2f(0.f, -S) };
				FSlateDrawElement::MakeLines(OutDrawElements, L + 1, Geo, Diamond, ESlateDrawEffect::None, LSUI::Brass, true, M.bTracked ? 4.f : 2.5f);
				if (M.bTracked)
				{
					FSlateDrawElement::MakeLines(OutDrawElements, L + 1, Geo, Circle(P, 18.f), ESlateDrawEffect::None, LSUI::Brass, true, 2.f);
				}
				break;
			}
			case ELSMapMarkerKind::FastTravel:
				FSlateDrawElement::MakeLines(OutDrawElements, L, Geo, Circle(P, 9.f, 6), ESlateDrawEffect::None, TravelColor, true, 3.f);
				break;
			}
		}

		// Player pins.
		for (const FVector& Pin : Story->GetMapPins())
		{
			const FVector2f P = ToScreen(Pin);
			FSlateDrawElement::MakeLines(OutDrawElements, L + 2, Geo, TArray<FVector2f>{ P, P + FVector2f(0.f, -22.f) }, ESlateDrawEffect::None, PinColor, true, 3.f);
			FSlateDrawElement::MakeLines(OutDrawElements, L + 2, Geo, Circle(P + FVector2f(0.f, -26.f), 6.f), ESlateDrawEffect::None, PinColor, true, 4.f);
		}
	}

	// Kieran: an arrow at his position, pointing where he faces.
	if (const APlayerController* PC = GetOwningPlayer())
	{
		if (const APawn* Pawn = PC->GetPawn())
		{
			const FVector2f P = ToScreen(Pawn->GetActorLocation());
			// Image space: up is north (+X), right is east (+Y).
			const FVector F = Pawn->GetActorForwardVector();
			const FVector2f Dir = FVector2f(F.Y, -F.X).GetSafeNormal();
			const FVector2f Side2(-Dir.Y, Dir.X);
			const TArray<FVector2f> Arrow{ P + Dir * 14.f, P - Dir * 8.f + Side2 * 8.f, P - Dir * 4.f, P - Dir * 8.f - Side2 * 8.f, P + Dir * 14.f };
			FSlateDrawElement::MakeLines(OutDrawElements, L + 3, Geo, Arrow, ESlateDrawEffect::None, PlayerColor, true, 3.f);
		}
	}

	// Title, compass rose and hint.
	FSlateDrawElement::MakeText(OutDrawElements, L + 3, Box(TL + FVector2f(14.f, 10.f), FVector2f(500.f, 30.f)),
		B->MapTitle.IsEmpty() ? FString(TEXT("Map")) : B->MapTitle.ToString(), FCoreStyle::GetDefaultFontStyle("Bold", 24), ESlateDrawEffect::None, InkColor);
	FSlateDrawElement::MakeText(OutDrawElements, L + 3, Box(TL + FVector2f(Side - 40.f, 12.f), FVector2f(30.f, 30.f)), TEXT("N"),
		FCoreStyle::GetDefaultFontStyle("Bold", 20), ESlateDrawEffect::None, InkColor);
	FSlateDrawElement::MakeLines(OutDrawElements, L + 3, Geo,
		TArray<FVector2f>{ TL + FVector2f(Side - 33.f, 70.f), TL + FVector2f(Side - 33.f, 40.f) }, ESlateDrawEffect::None, InkColor, true, 3.f);
	FSlateDrawElement::MakeText(OutDrawElements, L + 3, Box(TL + FVector2f(14.f, Side - 28.f), FVector2f(700.f, 24.f)),
		LOCTEXT("Hint", "Click to place a pin (up to 3), click a pin to remove it.  M or Esc to close").ToString(), SmallFont, ESlateDrawEffect::None, InkColor);
	return L + 4;
}

FReply ULSMapWidget::NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent)
{
	if (InMouseEvent.GetEffectingButton() != EKeys::LeftMouseButton)
	{
		return FReply::Unhandled();
	}
	const FSlateRect R = MapRect(InGeometry);
	const FVector2D Local = InGeometry.AbsoluteToLocal(InMouseEvent.GetScreenSpacePosition());
	if (Local.X < R.Left || Local.X > R.Right || Local.Y < R.Top || Local.Y > R.Bottom)
	{
		return FReply::Handled();
	}
	const float Side = R.Right - R.Left;
	const FVector2D Map((Local.X - R.Left) / Side, (Local.Y - R.Top) / Side);

	// A click near an existing pin removes it (pins are drawn with their head above the point).
	if (const ALSMapBounds* B = MapBounds.Get())
	{
		if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
		{
			const TArray<FVector>& Pins = Story->GetMapPins();
			for (int32 i = 0; i < Pins.Num(); ++i)
			{
				const FVector2D P = B->WorldToMap(Pins[i]) * Side + FVector2D(R.Left, R.Top);
				if (FVector2D::Distance(P, Local) < PinPickRadius || FVector2D::Distance(P - FVector2D(0.f, 26.f), Local) < PinPickRadius)
				{
					Story->RemoveMapPin(i);
					return FReply::Handled();
				}
			}
		}
	}
	ClickAt(Map);
	return FReply::Handled();
}

void ULSMapWidget::ClickAt(const FVector2D& Map)
{
	const ALSMapBounds* B = MapBounds.Get();
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!B || !Story)
	{
		return;
	}
	float Z = 0.f;
	if (const APlayerController* PC = GetOwningPlayer())
	{
		if (const APawn* Pawn = PC->GetPawn())
		{
			Z = Pawn->GetActorLocation().Z;
		}
	}
	Story->AddMapPin(B->MapToWorld(Map, Z));
	UE_LOG(LogTemp, Display, TEXT("LS_UI map pin added (%d pins)"), Story->GetMapPins().Num());
}

#undef LOCTEXT_NAMESPACE

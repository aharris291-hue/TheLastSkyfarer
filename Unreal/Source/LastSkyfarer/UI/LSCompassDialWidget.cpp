// The Last Skyfarer: brass compass dial.

#include "LSCompassDialWidget.h"

#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "LSUIHelpers.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

namespace
{
	// Aerian glow (STYLE_GUIDE): sky blue for impossible routes.
	const FLinearColor AerianBlue = FLinearColor::FromSRGBColor(FColor(0x4B, 0xB3, 0xFF));
}

void ULSCompassDialWidget::ShowReading(const FLSCompassReading& Reading, float NeedleYaw)
{
	Timer = ShowTime;
	bHasTarget = Reading.bHasTarget;
	bImpossible = Reading.bImpossibleRoute;
	Distance = Reading.Distance;
	Needle = NeedleYaw;
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

void ULSCompassDialWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);
	if (Timer > 0.f)
	{
		Timer -= InDeltaTime;
		// The needle swings onto its bearing like a real compass.
		DisplayNeedle = FMath::FInterpTo(DisplayNeedle, Needle, InDeltaTime, 6.f);
		SetRenderOpacity(FMath::Clamp(Timer / 0.5f, 0.f, 1.f));
		if (Timer <= 0.f)
		{
			SetVisibility(ESlateVisibility::Collapsed);
		}
	}
}

int32 ULSCompassDialWidget::NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
	FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	LayerId = Super::NativePaint(Args, AllottedGeometry, MyCullingRect, OutDrawElements, LayerId, InWidgetStyle, bParentEnabled);
	const FVector2f Size = FVector2f(AllottedGeometry.GetLocalSize());
	// Top centre, just below the location banner.
	const FVector2f C(Size.X * 0.5f, 130.f + Radius);
	const FPaintGeometry Geo = AllottedGeometry.ToPaintGeometry();

	// Face and brass ring.
	TArray<FVector2f> Ring;
	for (int32 i = 0; i <= 48; ++i)
	{
		const float A = 2.f * PI * i / 48.f;
		Ring.Add(C + FVector2f(FMath::Sin(A), -FMath::Cos(A)) * Radius);
	}
	FSlateDrawElement::MakeBox(OutDrawElements, LayerId, AllottedGeometry.ToPaintGeometry(FVector2f(Radius * 2.f, Radius * 2.f), FSlateLayoutTransform(FVector2f(C.X - Radius, C.Y - Radius))),
		FCoreStyle::Get().GetBrush("WhiteBrush"), ESlateDrawEffect::None, LSUI::PanelTint);
	FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 1, Geo, Ring, ESlateDrawEffect::None, LSUI::Brass, true, 3.f);

	// Ticks every 45 degrees (relative to the view: the top tick is straight ahead).
	for (int32 i = 0; i < 8; ++i)
	{
		const float A = 2.f * PI * i / 8.f;
		const FVector2f Dir(FMath::Sin(A), -FMath::Cos(A));
		const float Inner = i % 2 == 0 ? 0.72f : 0.84f;
		FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 1, Geo, TArray<FVector2f>{ C + Dir * Radius * Inner, C + Dir * Radius }, ESlateDrawEffect::None, LSUI::Brass, true, 2.f);
	}

	// Needle: points at the target, or spins idly when there is none.
	const float Yaw = bHasTarget ? DisplayNeedle : FMath::Fmod(Timer * 360.f, 360.f);
	const float R = FMath::DegreesToRadians(Yaw);
	const FVector2f Tip = C + FVector2f(FMath::Sin(R), -FMath::Cos(R)) * Radius * 0.8f;
	const FVector2f Tail = C - FVector2f(FMath::Sin(R), -FMath::Cos(R)) * Radius * 0.35f;
	const FLinearColor NeedleColor = bImpossible ? AerianBlue : FLinearColor(0.75f, 0.18f, 0.12f);
	FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 2, Geo, TArray<FVector2f>{ Tail, Tip }, ESlateDrawEffect::None, NeedleColor, true, 4.f);
	if (bImpossible)
	{
		// The engraved ring glows when the compass senses an impossible route.
		FSlateDrawElement::MakeLines(OutDrawElements, LayerId + 2, Geo, Ring, ESlateDrawEffect::None, AerianBlue * FLinearColor(1.f, 1.f, 1.f, 0.6f), true, 6.f);
	}
	return LayerId + 3;
}

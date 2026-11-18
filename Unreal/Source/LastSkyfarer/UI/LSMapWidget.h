// The Last Skyfarer: map screen (GDD 9): the level from above, markers, Kieran and up to 3 player pins.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "LSMapWidget.generated.h"

class ALSMapBounds;

/**
 * Placeholder look: the top-down capture tinted like parchment, markers drawn in pencil (rumoured,
 * with "?") or ink (known), the tracked objective highlighted in brass. Click to place a pin; click a
 * pin to remove it.
 */
UCLASS()
class LASTSKYFARER_API ULSMapWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Call when the map opens. */
	void Refresh();

	/** Number of markers drawn last time (for tests and logs). */
	int32 GetDrawnMarkerCount() const { return DrawnMarkers; }

	/** Screen-independent pin placement for scripted checks: Map is 0..1 across the map square. */
	void ClickAt(const FVector2D& Map);

protected:
	virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FReply NativeOnMouseButtonDown(const FGeometry& InGeometry, const FPointerEvent& InMouseEvent) override;
	virtual bool NativeSupportsKeyboardFocus() const override { return true; }

private:
	TWeakObjectPtr<ALSMapBounds> MapBounds;
	FSlateBrush MapBrush;
	mutable int32 DrawnMarkers = 0;

	/** The square the map is drawn in, in local widget space. */
	FSlateRect MapRect(const FGeometry& Geometry) const;
};

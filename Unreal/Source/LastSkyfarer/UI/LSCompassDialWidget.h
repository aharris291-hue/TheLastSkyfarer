// The Last Skyfarer: brass compass dial shown at the top of the screen while the compass pulses (GDD 3).

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSCompassComponent.h"
#include "LSCompassDialWidget.generated.h"

/** Drawn in code: a ring, cardinal ticks and a needle. Fades out after ShowTime. */
UCLASS()
class LASTSKYFARER_API ULSCompassDialWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Compass")
	float ShowTime = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Compass")
	float Radius = 46.f;

	/** Show a reading. NeedleYaw is degrees relative to the camera (0 = straight ahead, + = right). */
	void ShowReading(const FLSCompassReading& Reading, float NeedleYaw);

	bool IsShowing() const { return Timer > 0.f; }
	float GetNeedleYaw() const { return Needle; }

protected:
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
	virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect,
		FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;

private:
	float Timer = 0.f;
	float Needle = 0.f;
	float DisplayNeedle = 0.f;
	bool bHasTarget = false;
	bool bImpossible = false;
	float Distance = 0.f;
};

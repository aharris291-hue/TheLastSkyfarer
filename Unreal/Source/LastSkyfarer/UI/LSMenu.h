// The Last Skyfarer: menu buttons for the code-built menus (title, settings, pause).

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "LSMenu.generated.h"

class UButton;
class UTextBlock;
class UWidgetTree;

/** Routes a button's OnClicked to a C++ lambda. Keep a reference to it (UPROPERTY) for as long as the button lives. */
UCLASS()
class LASTSKYFARER_API ULSClickProxy : public UObject
{
	GENERATED_BODY()

public:
	TFunction<void()> Fn;

	UFUNCTION() void Click() { if (Fn) { Fn(); } }
};

namespace LSUI
{
	/** A placeholder-styled, focusable menu button (works with mouse and gamepad) that runs Fn when pressed. */
	LASTSKYFARER_API UButton* MakeMenuButton(UWidgetTree* Tree, const FText& Label, int32 Size, UObject* Owner,
		TArray<TObjectPtr<ULSClickProxy>>& Keep, TFunction<void()> Fn, UTextBlock** OutLabel = nullptr);
}

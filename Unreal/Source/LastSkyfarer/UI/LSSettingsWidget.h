// The Last Skyfarer: Settings panel (volumes, look sensitivity, invert Y, subtitles).

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSSettingsWidget.generated.h"

class UButton;
class UTextBlock;
class ULSClickProxy;

/** Each row has < and > buttons, so it works with the mouse and the gamepad alike. Changes save at once. */
UCLASS()
class LASTSKYFARER_API ULSSettingsWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	DECLARE_MULTICAST_DELEGATE(FOnBack);
	FOnBack OnBack;

	/** Gives the first control keyboard and gamepad focus. */
	void FocusFirst();

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	UPROPERTY() TArray<TObjectPtr<ULSClickProxy>> Proxies;
	UPROPERTY() TObjectPtr<UButton> FirstButton;
	UPROPERTY() TArray<TObjectPtr<UTextBlock>> Values;
	TArray<TFunction<FText()>> RowShows;

	void Refresh();
};

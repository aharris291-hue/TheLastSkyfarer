// The Last Skyfarer: title screen (New Game, Continue, Settings, Quit).

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSTitleWidget.generated.h"

class UButton;
class UTextBlock;
class UVerticalBox;
class ULSClickProxy;
class ULSSettingsWidget;

UCLASS()
class LASTSKYFARER_API ULSTitleWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	static const TCHAR* BrindleMap;
	static const TCHAR* TitleMap;

	/** The newest of the autosave and the manual save, or empty if there is none. */
	static FString NewestSlot();

	void NewGame();
	/** Loads the newest save and opens Brindle Isle where it was saved. False if there is no save. */
	bool Continue();
	bool CanContinue() const { return !NewestSlot().IsEmpty(); }
	void FocusFirst();

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeConstruct() override;

private:
	UPROPERTY() TArray<TObjectPtr<ULSClickProxy>> Proxies;
	UPROPERTY() TObjectPtr<UVerticalBox> MainColumn;
	UPROPERTY() TObjectPtr<UButton> FirstButton;
	UPROPERTY() TObjectPtr<UButton> ContinueButton;
	UPROPERTY() TObjectPtr<ULSSettingsWidget> Settings;

	void ShowSettings(bool bShow);
};

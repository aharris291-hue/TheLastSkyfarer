// The Last Skyfarer: pause menu with Resume, Save, Load and Quit.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSPauseWidget.generated.h"

class UTextBlock;
class ULSStorySubsystem;

UCLASS()
class LASTSKYFARER_API ULSPauseWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Save slot used by the menu. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pause")
	FString SlotName = TEXT("slot1");

	void SetStory(ULSStorySubsystem* Story) { StoryRef = Story; }

	DECLARE_MULTICAST_DELEGATE(FOnResume);
	FOnResume OnResume;

	UFUNCTION(BlueprintCallable, Category = "Pause") void Save();
	UFUNCTION(BlueprintCallable, Category = "Pause") void Load();

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	UPROPERTY() TObjectPtr<UTextBlock> StatusText;
	TWeakObjectPtr<ULSStorySubsystem> StoryRef;

	UFUNCTION() void HandleResume();
	UFUNCTION() void HandleSave();
	UFUNCTION() void HandleLoad();
	UFUNCTION() void HandleQuit();
};

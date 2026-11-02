// The Last Skyfarer: in-game HUD: quest tracker, toasts, interaction prompt and dialogue box.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSNarrativeTypes.h"
#include "LSHUDWidget.generated.h"

class UBorder;
class UButton;
class UTextBlock;
class UVerticalBox;
class ULSStorySubsystem;

/**
 * Built in code (no asset needed). GDD 15: minimal HUD; the objective shows for a few seconds after
 * it changes, then fades (ShowTracker brings it back).
 */
UCLASS()
class LASTSKYFARER_API ULSHUDWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Seconds the quest tracker stays after a change. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD")
	float TrackerShowTime = 6.f;

	/** Seconds a toast stays. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD")
	float ToastTime = 3.5f;

	void BindStory(ULSStorySubsystem* Story);

	UFUNCTION(BlueprintCallable, Category = "HUD")
	void ShowToast(const FText& Message);

	UFUNCTION(BlueprintCallable, Category = "HUD")
	void SetPrompt(const FText& Prompt);

	UFUNCTION(BlueprintCallable, Category = "HUD")
	void ShowTracker();

	UFUNCTION(BlueprintCallable, Category = "HUD")
	void RefreshTracker();

	UFUNCTION(BlueprintPure, Category = "HUD")
	bool IsDialogueOpen() const { return bDialogueOpen; }

	/** The text currently in the dialogue box (for tests and logs). */
	FText GetDialogueText() const;
	FText GetDialogueSpeaker() const;

	/** Clicked the dialogue box. */
	DECLARE_MULTICAST_DELEGATE(FOnAdvance);
	FOnAdvance OnAdvanceClicked;

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	UPROPERTY() TObjectPtr<UVerticalBox> TrackerBox;
	UPROPERTY() TObjectPtr<UTextBlock> TrackerTitle;
	UPROPERTY() TObjectPtr<UVerticalBox> TrackerObjectives;
	UPROPERTY() TObjectPtr<UBorder> ToastPanel;
	UPROPERTY() TObjectPtr<UTextBlock> ToastText;
	UPROPERTY() TObjectPtr<UBorder> PromptPanel;
	UPROPERTY() TObjectPtr<UTextBlock> PromptText;
	UPROPERTY() TObjectPtr<UButton> DialogueButton;
	UPROPERTY() TObjectPtr<UTextBlock> SpeakerText;
	UPROPERTY() TObjectPtr<UTextBlock> LineText;
	UPROPERTY() TWeakObjectPtr<ULSStorySubsystem> StoryRef;

	float TrackerTimer = 0.f;
	float ToastTimer = 0.f;
	bool bDialogueOpen = false;

	UFUNCTION() void HandleLine(FName ConversationId, const FLSDialogueLine& Line);
	UFUNCTION() void HandleEnded(FName ConversationId);
	UFUNCTION() void HandleNotify(const FText& Message);
	UFUNCTION() void HandleQuestChanged(FName QuestId, ELSQuestState State);
	UFUNCTION() void HandleDialogueClicked();
};

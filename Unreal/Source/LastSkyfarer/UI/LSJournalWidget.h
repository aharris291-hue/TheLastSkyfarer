// The Last Skyfarer: journal screen with the four tabs from GDD 9.

#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LSJournalWidget.generated.h"

class UButton;
class UScrollBox;
class UTextBlock;
class ULSStorySubsystem;

UENUM(BlueprintType)
enum class ELSJournalTab : uint8
{
	Quests,
	Discoveries,
	Elias,
	Piko
};

UCLASS()
class LASTSKYFARER_API ULSJournalWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void SetStory(ULSStorySubsystem* Story) { StoryRef = Story; }

	UFUNCTION(BlueprintCallable, Category = "Journal")
	void ShowTab(ELSJournalTab Tab);

	UFUNCTION(BlueprintPure, Category = "Journal")
	ELSJournalTab GetTab() const { return CurrentTab; }

	/** Number of entries listed on the current tab (for tests and logs). */
	int32 GetEntryCount() const { return EntryCount; }

protected:
	virtual TSharedRef<SWidget> RebuildWidget() override;

private:
	UPROPERTY() TObjectPtr<UScrollBox> Content;
	UPROPERTY() TArray<TObjectPtr<UButton>> TabButtons;
	UPROPERTY() TArray<TObjectPtr<UTextBlock>> TabLabels;
	TWeakObjectPtr<ULSStorySubsystem> StoryRef;
	ELSJournalTab CurrentTab = ELSJournalTab::Quests;
	int32 EntryCount = 0;

	void AddHeading(const FText& Text);
	void AddBody(const FText& Text, bool bDim = false);
	void AddEmpty(const FText& Text);
	void FillQuests();
	void FillJournalKind(FName Kind, const FText& EmptyText);
	void FillDiscoveries();

	UFUNCTION() void OnQuestsTab();
	UFUNCTION() void OnDiscoveriesTab();
	UFUNCTION() void OnEliasTab();
	UFUNCTION() void OnPikoTab();
};

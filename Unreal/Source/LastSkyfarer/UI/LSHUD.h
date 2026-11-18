// The Last Skyfarer: HUD actor that owns the widgets and connects them to the story and the player.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "LSHUD.generated.h"

class ULSHUDWidget;
class ULSJournalWidget;
class ULSPauseWidget;
class ULSMapWidget;
class ULSCompassDialWidget;
class ULSCompassComponent;
struct FLSCompassReading;
class ULSInteractorComponent;
class ULSInteractableComponent;

UCLASS()
class LASTSKYFARER_API ALSHUD : public AHUD
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintCallable, Category = "UI") void ToggleJournal();
	UFUNCTION(BlueprintCallable, Category = "UI") void TogglePause();
	UFUNCTION(BlueprintCallable, Category = "UI") void PeekTracker();
	UFUNCTION(BlueprintCallable, Category = "UI") void ToggleMap();
	UFUNCTION(BlueprintPure, Category = "UI") bool IsMapOpen() const { return bMapOpen; }

	UFUNCTION(BlueprintPure, Category = "UI") bool IsJournalOpen() const { return bJournalOpen; }
	UFUNCTION(BlueprintPure, Category = "UI") bool IsPauseOpen() const { return bPauseOpen; }

	ULSHUDWidget* GetHUDWidget() const { return HUDWidget; }
	ULSJournalWidget* GetJournalWidget() const { return JournalWidget; }
	ULSPauseWidget* GetPauseWidget() const { return PauseWidget; }
	ULSMapWidget* GetMapWidget() const { return MapWidget; }
	ULSCompassDialWidget* GetCompassDial() const { return CompassDial; }

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY() TObjectPtr<ULSHUDWidget> HUDWidget;
	UPROPERTY() TObjectPtr<ULSJournalWidget> JournalWidget;
	UPROPERTY() TObjectPtr<ULSPauseWidget> PauseWidget;
	UPROPERTY() TObjectPtr<ULSMapWidget> MapWidget;
	UPROPERTY() TObjectPtr<ULSCompassDialWidget> CompassDial;
	TWeakObjectPtr<ULSCompassComponent> BoundCompass;
	bool bMapOpen = false;
	TWeakObjectPtr<ULSInteractorComponent> BoundInteractor;
	bool bJournalOpen = false;
	bool bPauseOpen = false;

	void UpdateInputMode();
	void AdvanceDialogue();

	UFUNCTION() void HandleTargetChanged(ULSInteractableComponent* Target, FText Prompt);
	UFUNCTION() void HandleDialogueLine(FName ConversationId, const struct FLSDialogueLine& Line);
	UFUNCTION() void HandleDialogueEnded(FName ConversationId);
	UFUNCTION() void HandleCompassPulse(const FLSCompassReading& Reading);
};

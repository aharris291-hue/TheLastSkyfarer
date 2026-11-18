// The Last Skyfarer: lets the player find and use interactables, and advance dialogue.
// Add to Kieran and bind the Interact input to Interact().

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LSInteractorComponent.generated.h"

class ULSInteractableComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FLSOnInteractTargetChanged, ULSInteractableComponent*, Target, FText, Prompt);

UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API ULSInteractorComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULSInteractorComponent();

	/** Seconds between target searches. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Interaction")
	float SearchInterval = 0.1f;

	/** Current target (for the prompt). Null while in dialogue. */
	UFUNCTION(BlueprintPure, Category = "Interaction")
	ULSInteractableComponent* GetTarget() const { return Target.Get(); }

	/** Prompt for the HUD, e.g. "Talk". Empty when there is no target. */
	UFUNCTION(BlueprintPure, Category = "Interaction")
	FText GetPrompt() const;

	/** Advances dialogue if one is running, otherwise uses the current target. */
	UFUNCTION(BlueprintCallable, Category = "Interaction")
	bool Interact();

	UPROPERTY(BlueprintAssignable, Category = "Interaction")
	FLSOnInteractTargetChanged OnTargetChanged;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Re-run the search now. */
	void RefreshTarget();

private:
	TWeakObjectPtr<ULSInteractableComponent> Target;
	float SearchTimer = 0.f;
};

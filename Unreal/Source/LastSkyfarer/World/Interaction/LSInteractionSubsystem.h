// The Last Skyfarer: registry of interactables in the world, for fast nearest-target queries.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "LSInteractionSubsystem.generated.h"

class ULSInteractableComponent;
class ULSStorySubsystem;

UCLASS()
class LASTSKYFARER_API ULSInteractionSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	void Register(ULSInteractableComponent* Interactable) { Interactables.AddUnique(Interactable); }
	void Unregister(ULSInteractableComponent* Interactable) { Interactables.Remove(Interactable); }

	/**
	 * Best target for a player at Location facing Forward: usable, within its radius, and
	 * scoring distance plus a penalty for being behind. Null if none.
	 */
	ULSInteractableComponent* FindBest(const FVector& Location, const FVector& Forward, const ULSStorySubsystem& Story) const;

	const TArray<TWeakObjectPtr<ULSInteractableComponent>>& GetAll() const { return Interactables; }

private:
	TArray<TWeakObjectPtr<ULSInteractableComponent>> Interactables;
};

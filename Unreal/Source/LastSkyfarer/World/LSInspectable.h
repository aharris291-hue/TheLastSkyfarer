// The Last Skyfarer: something to look at or use (bulletin board, fountain, windmill, doors).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInspectable.generated.h"

class UStaticMeshComponent;
class ULSInteractableComponent;

/** A static mesh with an interactable: set Interactable's Prompt and Rules (conversations and actions). */
UCLASS(Blueprintable)
class LASTSKYFARER_API ALSInspectable : public AActor
{
	GENERATED_BODY()

public:
	ALSInspectable();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Inspect")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Inspect")
	TObjectPtr<ULSInteractableComponent> Interactable;
};

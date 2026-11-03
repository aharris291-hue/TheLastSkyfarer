// The Last Skyfarer: save game container. Written atomically by ULSStorySubsystem.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "LSNarrativeTypes.h"
#include "LSSaveGame.generated.h"

UCLASS()
class LASTSKYFARER_API ULSSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY(SaveGame)
	FLSStorySaveData Data;

	UPROPERTY(SaveGame)
	FDateTime SavedAt;
};

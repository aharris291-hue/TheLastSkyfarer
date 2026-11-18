// The Last Skyfarer: a placeable map marker (landmark, objective or fast travel).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSMapMarkerActor.generated.h"

class ULSMapMarkerComponent;

/** Holds one ULSMapMarkerComponent so markers can be placed by level scripts. Not visible in game. */
UCLASS()
class LASTSKYFARER_API ALSMapMarkerActor : public AActor
{
	GENERATED_BODY()

public:
	ALSMapMarkerActor();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Map")
	TObjectPtr<ULSMapMarkerComponent> Marker;
};

// The Last Skyfarer: a mesh that turns steadily (windmill sails).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSSpinningMesh.generated.h"

class UStaticMeshComponent;

/** Spins its mesh around its local Y axis (the sails' axle). No collision; purely visual. */
UCLASS()
class LASTSKYFARER_API ALSSpinningMesh : public AActor
{
	GENERATED_BODY()

public:
	ALSSpinningMesh();
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Spin")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Degrees per second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spin")
	float Speed = 24.f;

	/** Played now and then from the hub (windmill creaks); none = silent. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spin")
	TArray<TObjectPtr<class USoundBase>> Creaks;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spin")
	TObjectPtr<class USoundAttenuation> CreakAttenuation;

private:
	float CreakTimer = 2.f;
};

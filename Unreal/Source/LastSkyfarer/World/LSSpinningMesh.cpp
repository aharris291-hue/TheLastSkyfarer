// The Last Skyfarer: a mesh that turns steadily (windmill sails).

#include "LSSpinningMesh.h"

#include "Components/StaticMeshComponent.h"

ALSSpinningMesh::ALSSpinningMesh()
{
	PrimaryActorTick.bCanEverTick = true;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void ALSSpinningMesh::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Mesh->AddLocalRotation(FRotator(Speed * DeltaSeconds, 0.f, 0.f));
}

// The Last Skyfarer: a mesh that turns steadily (windmill sails).

#include "LSSpinningMesh.h"

#include "Components/StaticMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"

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
	CreakTimer -= DeltaSeconds;
	if (CreakTimer <= 0.f && Creaks.Num() > 0)
	{
		CreakTimer = FMath::FRandRange(4.f, 9.f);
		UGameplayStatics::PlaySoundAtLocation(this, Creaks[FMath::RandRange(0, Creaks.Num() - 1)], GetActorLocation(), FMath::FRandRange(0.6f, 0.9f),
			FMath::FRandRange(0.9f, 1.1f), 0.f, CreakAttenuation);
	}
}

// The Last Skyfarer: inspectable object.

#include "LSInspectable.h"

#include "Components/StaticMeshComponent.h"
#include "LSInteractableComponent.h"

ALSInspectable::ALSInspectable()
{
	PrimaryActorTick.bCanEverTick = false;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Interactable = CreateDefaultSubobject<ULSInteractableComponent>(TEXT("Interactable"));
	Interactable->SetupAttachment(Mesh);
}

// The Last Skyfarer: placeable map marker.

#include "LSMapMarkerActor.h"

#include "LSMapMarkerComponent.h"

ALSMapMarkerActor::ALSMapMarkerActor()
{
	PrimaryActorTick.bCanEverTick = false;
	Marker = CreateDefaultSubobject<ULSMapMarkerComponent>(TEXT("Marker"));
	RootComponent = Marker;
	SetHidden(true);
}

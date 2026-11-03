// The Last Skyfarer: player settings.

#include "LSSettings.h"

#include "AudioDevice.h"
#include "Engine/World.h"

void ULSSettings::SaveAndApply(const UObject* WorldContext)
{
	SaveConfig();
	Apply(WorldContext);
}

void ULSSettings::Apply(const UObject* WorldContext) const
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (FAudioDeviceHandle Device = World ? World->GetAudioDevice() : FAudioDeviceHandle())
	{
		Device->SetTransientPrimaryVolume(MasterVolume);
	}
}

// The Last Skyfarer: player settings (title screen Settings), saved per user in GameUserSettings.ini.

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "LSSettings.generated.h"

UCLASS(config = GameUserSettings)
class LASTSKYFARER_API ULSSettings : public UObject
{
	GENERATED_BODY()

public:
	static ULSSettings* Get() { return GetMutableDefault<ULSSettings>(); }

	/** 0..1. Master applies to the engine's primary volume; music and effects are kept for when audio arrives. */
	UPROPERTY(config) float MasterVolume = 1.f;
	UPROPERTY(config) float MusicVolume = 0.8f;
	UPROPERTY(config) float EffectsVolume = 1.f;

	/** Multiplier on mouse and stick look. */
	UPROPERTY(config) float LookSensitivity = 1.f;
	UPROPERTY(config) bool bInvertY = false;

	/** Subtitles for spoken lines (dialogue is text-only until voices are recorded). */
	UPROPERTY(config) bool bSubtitles = true;

	/** Saves to disk and applies what can be applied now (master volume). */
	void SaveAndApply(const UObject* WorldContext);
	void Apply(const UObject* WorldContext) const;
};

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

	/** Graphics preset: 0 Low, 1 Medium, 2 High, 3 Epic; -1 = not chosen yet (detected on first launch). */
	UPROPERTY(config) int32 Quality = -1;
	/** Percent of the window resolution the 3D view renders at (50..100). */
	UPROPERTY(config) int32 ResolutionScale = 100;
	UPROPERTY(config) bool bVSync = true;
	/** Frame rate cap; 0 = unlimited. */
	UPROPERTY(config) int32 FrameCap = 60;

	static FText QualityName(int32 Level);

	/** Picks a preset for this PC: Low on integrated graphics or without DirectX 12 SM6, otherwise from the engine's benchmark. */
	static int32 DetectQuality();

	/** Saves to disk and applies everything. */
	void SaveAndApply(const UObject* WorldContext);
	/** Applies volume and graphics; detects the graphics preset on first use. -LSQuality=N overrides the preset (not saved). */
	void Apply(const UObject* WorldContext);

	/** The preset in use (after any -LSQuality override). */
	int32 GetEffectiveQuality() const;
};

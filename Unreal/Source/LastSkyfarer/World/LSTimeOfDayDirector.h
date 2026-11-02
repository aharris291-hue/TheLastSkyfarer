// The Last Skyfarer: switches sun, sky and fog between story time-of-day presets (GDD 13, D-21).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSTimeOfDayDirector.generated.h"

class ADirectionalLight;
class ASkyLight;
class AExponentialHeightFog;

/** One lighting preset. Colours follow the STYLE_GUIDE Act I colour script. */
USTRUCT(BlueprintType)
struct FLSTimeOfDayPreset
{
	GENERATED_BODY()

	/** Sun rotation (pitch below zero points down, i.e. the sun is above the horizon). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day") FRotator SunRotation = FRotator(-25.f, 60.f, 0.f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day") FLinearColor SunColor = FLinearColor::White;
	/** Lux. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day") float SunIntensity = 8.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day") float SkyIntensity = 1.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day") FLinearColor FogColor = FLinearColor(0.6f, 0.7f, 0.85f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day") float FogDensity = 0.01f;
};

/**
 * Listens to ULSStorySubsystem::OnTimeOfDayChanged and blends the level's directional light,
 * sky light and height fog to the matching preset. Placed or spawned once per level.
 */
UCLASS()
class LASTSKYFARER_API ALSTimeOfDayDirector : public AActor
{
	GENERATED_BODY()

public:
	ALSTimeOfDayDirector();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day")
	TMap<FName, FLSTimeOfDayPreset> Presets;

	/** Seconds to blend between presets. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Time of day")
	float BlendTime = 3.f;

	/** Apply a preset (blends unless bInstant). */
	UFUNCTION(BlueprintCallable, Category = "Time of day")
	void ApplyTimeOfDay(FName TimeOfDay, bool bInstant = false);

	UFUNCTION(BlueprintPure, Category = "Time of day")
	FName GetCurrent() const { return Current; }

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	TWeakObjectPtr<ADirectionalLight> Sun;
	TWeakObjectPtr<ASkyLight> Sky;
	TWeakObjectPtr<AExponentialHeightFog> Fog;
	FName Current;
	FLSTimeOfDayPreset From;
	FLSTimeOfDayPreset To;
	float BlendAlpha = 1.f;

	void FindLights();
	FLSTimeOfDayPreset Capture() const;
	void Apply(const FLSTimeOfDayPreset& P);

	UFUNCTION() void HandleTimeOfDay(FName TimeOfDay);
};

// The Last Skyfarer: Kieran's sounds (wind by altitude and speed, glide layers, footsteps by surface).

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LSPlayerAudioComponent.generated.h"

class UAudioComponent;
class USoundBase;

/**
 * The core wind is two looping layers: a low rumble that is always there outdoors and a high, whistling layer that
 * rises with altitude above the island and with speed. While gliding, an air rush and the glider's cloth flutter
 * join in. Footsteps play on the ground at a pace set by speed, picking grass, stone or wood from the material
 * under Kieran's feet.
 */
UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API ULSPlayerAudioComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULSPlayerAudioComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Island surface height, cm; altitude for the wind is measured from here. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	float GroundHeight = 0.f;

	/** Altitude above GroundHeight, m, at which the high wind is at full strength. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	float FullWindAltitude = 60.f;

	/** Speed, m/s, at which the wind and rush layers are at full strength. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	float FullWindSpeed = 25.f;

	/** Indoors (the workshop) the wind is muffled to a whisper. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Audio")
	bool bIndoors = false;

	UFUNCTION(BlueprintPure, Category = "Audio") float GetWindLevel() const { return WindHigh; }
	UFUNCTION(BlueprintPure, Category = "Audio") int32 GetStepsPlayed() const { return StepsPlayed; }

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY() TObjectPtr<UAudioComponent> LowLayer;
	UPROPERTY() TObjectPtr<UAudioComponent> HighLayer;
	UPROPERTY() TObjectPtr<UAudioComponent> RushLayer;
	UPROPERTY() TObjectPtr<UAudioComponent> FlutterLayer;
	UPROPERTY() TArray<TObjectPtr<USoundBase>> GrassSteps;
	UPROPERTY() TArray<TObjectPtr<USoundBase>> StoneSteps;
	UPROPERTY() TArray<TObjectPtr<USoundBase>> WoodSteps;

	float WindLow = 0.f;
	float WindHigh = 0.f;
	float Rush = 0.f;
	float StepTimer = 0.f;
	int32 LastStep = -1;
	int32 StepsPlayed = 0;

	UAudioComponent* MakeLayer(const TCHAR* Path);
	void PlayFootstep();
};

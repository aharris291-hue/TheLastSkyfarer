// The Last Skyfarer: game mode for system test maps (spawns Kieran and Piko).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "LSTestGameMode.generated.h"

class APikoCompanion;

/**
 * Spawns the player character and Piko. Command-line helpers for unattended checks:
 *   -LSShot=<seconds>   launch Kieran off the cliff into a glide, take a screenshot after <seconds>, then quit.
 */
UCLASS()
class LASTSKYFARER_API ALSTestGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ALSTestGameMode();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko")
	TSubclassOf<APikoCompanion> PikoClass;

	/** Where the scripted glide for the screenshot starts (cliff edge), cm. */
	UPROPERTY(EditAnywhere, Category = "Test")
	FVector ShotLaunchLocation = FVector(2600.f, 0.f, 1700.f);

	virtual void RestartPlayer(AController* NewPlayer) override;
	virtual void StartPlay() override;

private:
	void BeginScriptedGlide();
	void TakeShot();
};

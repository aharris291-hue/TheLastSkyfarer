// The Last Skyfarer: title screen map's game mode and HUD.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "LSTitleGameMode.generated.h"

class ULSTitleWidget;

/** No pawn: the view is the level's camera and the title menu takes the input. */
UCLASS()
class LASTSKYFARER_API ALSTitleGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ALSTitleGameMode();
};

/**
 * Shows the title menu over the level's first camera. For automated runs, -LSBrindleCheck presses New Game
 * and -LSContinueCheck presses Continue after a screenshot of the title screen.
 */
UCLASS()
class LASTSKYFARER_API ALSTitleHUD : public AHUD
{
	GENERATED_BODY()

public:
	ALSTitleHUD();
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY() TObjectPtr<ULSTitleWidget> Title;
	float Time = 0.f;
	bool bShot = false;
	bool bPressed = false;
};

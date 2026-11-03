// The Last Skyfarer: title screen map's game mode and HUD.

#include "LSTitleGameMode.h"

#include "Camera/CameraActor.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "LSSettings.h"
#include "LSTitleWidget.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

ALSTitleGameMode::ALSTitleGameMode()
{
	DefaultPawnClass = nullptr;
	HUDClass = ALSTitleHUD::StaticClass();
}

ALSTitleHUD::ALSTitleHUD()
{
	PrimaryActorTick.bCanEverTick = true;
}

void ALSTitleHUD::BeginPlay()
{
	Super::BeginPlay();
	APlayerController* PC = GetOwningPlayerController();
	for (TActorIterator<ACameraActor> It(GetWorld()); It; ++It)
	{
		PC->SetViewTarget(*It);
		break;
	}
	ULSSettings::Get()->Apply(this);

	Title = CreateWidget<ULSTitleWidget>(PC, ULSTitleWidget::StaticClass());
	Title->AddToViewport();
	FInputModeUIOnly Mode;
	Mode.SetWidgetToFocus(Title->TakeWidget());
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	PC->SetInputMode(Mode);
	PC->SetShowMouseCursor(true);
	Title->FocusFirst();
}

void ALSTitleHUD::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Time += DeltaSeconds;
	const bool bNewGameCheck = FParse::Param(FCommandLine::Get(), TEXT("LSBrindleCheck"));
	const bool bContinueCheck = FParse::Param(FCommandLine::Get(), TEXT("LSContinueCheck"));
	if (!Title || !(bNewGameCheck || bContinueCheck))
	{
		return;
	}
	if (Time > 2.f && !bShot)
	{
		bShot = true;
		const FString Dir = FPaths::ProjectSavedDir() / TEXT("Screenshots");
		IFileManager::Get().MakeDirectory(*Dir, true);
		FScreenshotRequest::RequestScreenshot(Dir / TEXT("L_Title.png"), true, false);
		UE_LOG(LogTemp, Display, TEXT("LS_TITLE screenshot, continue %s"), Title->CanContinue() ? TEXT("enabled") : TEXT("disabled"));
	}
	if (Time > 3.f && !bPressed)
	{
		bPressed = true;
		if (bContinueCheck)
		{
			UE_LOG(LogTemp, Display, TEXT("LS_TITLE ContinueAvailable %s"), Title->Continue() ? TEXT("PASS") : TEXT("FAIL"));
		}
		else
		{
			Title->NewGame();
		}
	}
}

// The Last Skyfarer: game mode for system test maps.

#include "LSTestGameMode.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GliderComponent.h"
#include "HAL/FileManager.h"
#include "LSPlayerCharacter.h"
#include "LSTraversalCheck.h"
#include "LSPlaythroughCheck.h"
#include "LSBrindleCheck.h"
#include "LSHUD.h"
#include "LSTimeOfDayDirector.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "PikoCompanion.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "UObject/ConstructorHelpers.h"

ALSTestGameMode::ALSTestGameMode()
{
	DefaultPawnClass = ALSPlayerCharacter::StaticClass();
	PikoClass = APikoCompanion::StaticClass();
	HUDClass = ALSHUD::StaticClass();

	// The template controller Blueprint adds the default input mapping contexts.
	static ConstructorHelpers::FClassFinder<APlayerController> PC(TEXT("/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController"));
	if (PC.Succeeded())
	{
		PlayerControllerClass = PC.Class;
	}
}

void ALSTestGameMode::RestartPlayer(AController* NewPlayer)
{
	Super::RestartPlayer(NewPlayer);
	if (NewPlayer && NewPlayer->GetPawn() && PikoClass)
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		APikoCompanion* Piko = GetWorld()->SpawnActor<APikoCompanion>(PikoClass, NewPlayer->GetPawn()->GetActorLocation(), FRotator::ZeroRotator, Params);
		if (Piko)
		{
			Piko->FollowTarget = NewPlayer->GetPawn();
		}
	}
}

void ALSTestGameMode::StartPlay()
{
	Super::StartPlay();
	GetWorld()->SpawnActor<ALSTimeOfDayDirector>();
	if (FParse::Param(FCommandLine::Get(), TEXT("LSBrindleCheck")))
	{
		GetWorld()->SpawnActor<ALSBrindleCheck>();
	}
	if (FParse::Param(FCommandLine::Get(), TEXT("LSPlaythrough")))
	{
		GetWorld()->SpawnActor<ALSPlaythroughCheck>();
	}
	if (FParse::Param(FCommandLine::Get(), TEXT("LSTraversalCheck")))
	{
		GetWorld()->SpawnActor<ALSTraversalCheck>();
	}
	float ShotDelay = 0.f;
	if (FParse::Value(FCommandLine::Get(), TEXT("LSShot="), ShotDelay) && ShotDelay > 0.f)
	{
		FTimerHandle Launch, Shot;
		GetWorldTimerManager().SetTimer(Launch, this, &ALSTestGameMode::BeginScriptedGlide, 2.f, false);
		GetWorldTimerManager().SetTimer(Shot, this, &ALSTestGameMode::TakeShot, 2.f + ShotDelay, false);
	}
}

void ALSTestGameMode::BeginScriptedGlide()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	ALSPlayerCharacter* Kieran = PC ? Cast<ALSPlayerCharacter>(PC->GetPawn()) : nullptr;
	if (!Kieran)
	{
		return;
	}
	Kieran->SetActorLocationAndRotation(ShotLaunchLocation, FRotator::ZeroRotator, false, nullptr, ETeleportType::TeleportPhysics);
	PC->SetControlRotation(FRotator(-12.f, 20.f, 0.f));
	UCharacterMovementComponent* Move = Kieran->GetCharacterMovement();
	Move->SetMovementMode(MOVE_Falling);
	Move->Velocity = FVector(1200.f, 0.f, 0.f);
	Kieran->Glider->TryDeploy();
}

void ALSTestGameMode::TakeShot()
{
	if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		if (const ALSPlayerCharacter* Kieran = Cast<ALSPlayerCharacter>(PC->GetPawn()))
		{
			UE_LOG(LogTemp, Display, TEXT("LS_SHOT Kieran at %s, gliding=%d, airspeed=%.1f m/s, path=%.1f deg, velocity=%s"),
				*Kieran->GetActorLocation().ToCompactString(), Kieran->Glider->IsGliding() ? 1 : 0,
				Kieran->Glider->GetAirspeed(), Kieran->Glider->GetState().PathAngle, *Kieran->GetVelocity().ToCompactString());
		}
	}
	for (TActorIterator<APikoCompanion> It(GetWorld()); It; ++It)
	{
		UE_LOG(LogTemp, Display, TEXT("LS_SHOT Piko at %s, glow=%.2f"), *It->GetActorLocation().ToCompactString(), It->MarkingGlow);
	}
	const FString Dir = FPaths::ProjectSavedDir() / TEXT("Screenshots");
	IFileManager::Get().MakeDirectory(*Dir, true);
	FScreenshotRequest::RequestScreenshot(Dir / TEXT("L_SystemsTest_glide.png"), false, false);
	FTimerHandle Quit;
	GetWorldTimerManager().SetTimer(Quit, [this]()
	{
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			PC->ConsoleCommand(TEXT("quit"));
		}
	}, 2.f, false);
}

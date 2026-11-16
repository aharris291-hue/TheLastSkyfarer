// The Last Skyfarer: Kieran's sounds.

#include "LSPlayerAudioComponent.h"

#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GliderComponent.h"
#include "Kismet/GameplayStatics.h"
#include "LSPlayerCharacter.h"
#include "Materials/MaterialInterface.h"
#include "Sound/ReverbEffect.h"
#include "Sound/SoundBase.h"

namespace
{
	const TCHAR* AudioRoot = TEXT("/Game/LastSkyfarer/Audio/");

	USoundBase* LoadSound(const FString& Path)
	{
		return LoadObject<USoundBase>(nullptr, *Path);
	}
}

ULSPlayerAudioComponent::ULSPlayerAudioComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

UAudioComponent* ULSPlayerAudioComponent::MakeLayer(const TCHAR* Name)
{
	USoundBase* Sound = LoadSound(FString(AudioRoot) + Name);
	if (!Sound)
	{
		return nullptr;
	}
	UAudioComponent* A = UGameplayStatics::CreateSound2D(this, Sound, 0.f, 1.f, 0.f, nullptr, true, false);
	if (A)
	{
		A->bAutoDestroy = false;
		A->Play(FMath::FRandRange(0.f, 4.f)); // start somewhere in the loop so layers do not phase together
	}
	return A;
}

void ULSPlayerAudioComponent::BeginPlay()
{
	Super::BeginPlay();
	LowLayer = MakeLayer(TEXT("Wind/wind_low_loop.wind_low_loop"));
	HighLayer = MakeLayer(TEXT("Wind/wind_high_loop.wind_high_loop"));
	RushLayer = MakeLayer(TEXT("Glide/glide_rush_loop.glide_rush_loop"));
	FlutterLayer = MakeLayer(TEXT("Glide/glider_flutter_loop.glider_flutter_loop"));
	for (int32 i = 1; i <= 3; ++i)
	{
		if (USoundBase* S = LoadSound(FString::Printf(TEXT("%sWind/wind_gust_%d.wind_gust_%d"), AudioRoot, i, i))) { Gusts.Add(S); }
	}
	DeploySound = LoadSound(FString(AudioRoot) + TEXT("Glide/glider_deploy.glider_deploy"));
	LandSound = LoadSound(FString(AudioRoot) + TEXT("Glide/glider_land.glider_land"));
	WorkshopReverb = LoadObject<UReverbEffect>(nullptr, *(FString(AudioRoot) + TEXT("Mix/RVB_Workshop.RVB_Workshop")));
	for (int32 i = 1; i <= 4; ++i)
	{
		for (const TCHAR* Kind : { TEXT("grass"), TEXT("stone"), TEXT("wood") })
		{
			if (USoundBase* S = LoadSound(FString::Printf(TEXT("%sFootsteps/step_%s_%d.step_%s_%d"), AudioRoot, Kind, i, Kind, i)))
			{
				(FCString::Strcmp(Kind, TEXT("grass")) == 0 ? GrassSteps : FCString::Strcmp(Kind, TEXT("stone")) == 0 ? StoneSteps : WoodSteps).Add(S);
			}
		}
	}
}

void ULSPlayerAudioComponent::PlayFootstep()
{
	const ACharacter* C = Cast<ACharacter>(GetOwner());
	if (!C)
	{
		return;
	}
	// The surface under the feet: the greybox collision underneath carries the painterly material names.
	const FVector Start = C->GetActorLocation();
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(LSFootstep), false, C);
	TArray<TObjectPtr<USoundBase>>* Set = &GrassSteps;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Start, Start - FVector(0.f, 0.f, 200.f), ECC_Visibility, Params) && Hit.GetComponent())
	{
		const UMaterialInterface* M = Hit.GetComponent()->GetMaterial(0);
		const FString Name = M ? M->GetName() : FString();
		if (Name.Contains(TEXT("Wood")))
		{
			Set = &WoodSteps;
		}
		else if (Name.Contains(TEXT("Stone")) || Name.Contains(TEXT("PathStone")) || Name.Contains(TEXT("Rock")))
		{
			Set = &StoneSteps;
		}
	}
	if (Set->Num() == 0)
	{
		return;
	}
	int32 Pick = FMath::RandRange(0, Set->Num() - 1);
	if (Pick == LastStep && Set->Num() > 1)
	{
		Pick = (Pick + 1) % Set->Num();
	}
	LastStep = Pick;
	UGameplayStatics::PlaySoundAtLocation(this, (*Set)[Pick], Start - FVector(0.f, 0.f, 90.f), FMath::FRandRange(0.7f, 0.9f), FMath::FRandRange(0.94f, 1.06f));
	++StepsPlayed;
}

void ULSPlayerAudioComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	const ALSPlayerCharacter* K = Cast<ALSPlayerCharacter>(GetOwner());
	if (!K)
	{
		return;
	}
	const bool bGliding = K->Glider && K->Glider->IsGliding();
	const float Speed = K->GetVelocity().Size() / 100.f;
	const float Altitude = (K->GetActorLocation().Z - GroundHeight) / 100.f;
	const float SpeedT = FMath::Clamp(Speed / FullWindSpeed, 0.f, 1.f);
	const float AltT = FMath::Clamp(Altitude / FullWindAltitude, 0.f, 1.f);
	const float Muffle = bIndoors ? 0.12f : 1.f;

	// Smooth towards targets so the wind breathes rather than jumps.
	const float A = FMath::Clamp(DeltaTime * 2.f, 0.f, 1.f);
	WindLow = FMath::Lerp(WindLow, Muffle * (0.35f + 0.35f * AltT + 0.3f * SpeedT), A);
	WindHigh = FMath::Lerp(WindHigh, Muffle * FMath::Clamp(0.08f + 0.6f * AltT + 0.5f * SpeedT, 0.f, 1.f), A);
	Rush = FMath::Lerp(Rush, bGliding ? 0.25f + 0.75f * SpeedT : 0.f, A);
	if (LowLayer) { LowLayer->SetVolumeMultiplier(FMath::Max(WindLow, 0.001f)); }
	if (HighLayer)
	{
		HighLayer->SetVolumeMultiplier(FMath::Max(WindHigh, 0.001f));
		HighLayer->SetPitchMultiplier(0.9f + 0.3f * SpeedT);
	}
	if (RushLayer)
	{
		RushLayer->SetVolumeMultiplier(FMath::Max(Rush * 0.8f, 0.001f));
		RushLayer->SetPitchMultiplier(0.85f + 0.4f * SpeedT);
	}
	if (FlutterLayer)
	{
		FlutterLayer->SetVolumeMultiplier(FMath::Max(Rush * 0.6f, 0.001f));
		FlutterLayer->SetPitchMultiplier(0.8f + 0.5f * SpeedT);
	}

	// Glider deploy and landing.
	if (bGliding != bWasGliding)
	{
		if (USoundBase* S = bGliding ? DeploySound.Get() : LandSound.Get())
		{
			UGameplayStatics::PlaySound2D(this, S, 0.8f);
		}
		bWasGliding = bGliding;
	}

	// Gusts swell over the wind now and then outdoors; more often up high and when fast.
	GustTimer -= DeltaTime;
	if (GustTimer <= 0.f && !bIndoors && Gusts.Num() > 0)
	{
		UGameplayStatics::PlaySound2D(this, Gusts[FMath::RandRange(0, Gusts.Num() - 1)], 0.25f + 0.5f * FMath::Max(AltT, SpeedT), FMath::FRandRange(0.9f, 1.1f));
		GustTimer = FMath::Lerp(14.f, 5.f, FMath::Max(AltT, SpeedT)) * FMath::FRandRange(0.7f, 1.3f);
	}

	// A warm wooden-room reverb inside the workshop.
	if (bIndoors != bReverbOn && WorkshopReverb)
	{
		bReverbOn = bIndoors;
		if (bReverbOn)
		{
			UGameplayStatics::ActivateReverbEffect(this, WorkshopReverb, TEXT("Workshop"), 1.f, 1.f, 0.5f);
		}
		else
		{
			UGameplayStatics::DeactivateReverbEffect(this, TEXT("Workshop"));
		}
	}

	// Footsteps on the ground, faster when running.
	const UCharacterMovementComponent* Move = K->GetCharacterMovement();
	if (Move && Move->IsMovingOnGround() && Speed > 0.6f)
	{
		StepTimer -= DeltaTime;
		if (StepTimer <= 0.f)
		{
			PlayFootstep();
			StepTimer = FMath::Clamp(0.62f - Speed * 0.045f, 0.28f, 0.6f);
		}
	}
	else
	{
		StepTimer = 0.f;
	}
}

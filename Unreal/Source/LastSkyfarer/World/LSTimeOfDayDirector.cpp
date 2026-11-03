// The Last Skyfarer: time-of-day lighting director.

#include "LSTimeOfDayDirector.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "EngineUtils.h"
#include "LSStorySubsystem.h"

namespace
{
	FLSTimeOfDayPreset MakePreset(const FRotator& Rot, const FLinearColor& SunColor, float Lux, float Sky, const FLinearColor& FogColor, float FogDensity)
	{
		FLSTimeOfDayPreset P;
		P.SunRotation = Rot;
		P.SunColor = SunColor;
		P.SunIntensity = Lux;
		P.SkyIntensity = Sky;
		P.FogColor = FogColor;
		P.FogDensity = FogDensity;
		return P;
	}
}

ALSTimeOfDayDirector::ALSTimeOfDayDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = false;

	// Starting values from the STYLE_GUIDE Act I colour script; tune in the editor.
	// Morning deliveries: clear warm daylight.
	Presets.Add(TEXT("Morning"), MakePreset(FRotator(-28.f, 60.f, 0.f), FLinearColor(1.f, 0.93f, 0.82f), 8.f, 1.f, FLinearColor(0.62f, 0.74f, 0.9f), 0.008f));
	// Letter of Inheritance: deep golden sunset, orange rim light.
	Presets.Add(TEXT("Sunset"), MakePreset(FRotator(-6.f, 250.f, 0.f), FLinearColor(1.f, 0.56f, 0.28f), 5.f, 0.6f, FLinearColor(0.95f, 0.58f, 0.38f), 0.014f));
	// Workshop at night: cool blue moonlight outside. The sun sets below the horizon (so the sky goes
	// dark) and a separate moon light takes over; exposure is pulled down so night stays night.
	FLSTimeOfDayPreset Night = MakePreset(FRotator(8.f, 200.f, 0.f), FLinearColor(0.55f, 0.66f, 1.f), 0.f, 0.15f, FLinearColor(0.03f, 0.04f, 0.09f), 0.018f);
	Night.MoonIntensity = 0.6f;
	Night.ExposureBias = -1.5f;
	Presets.Add(TEXT("Night"), Night);
	// Dawn launch: pale gold horizon over a lilac cloud sea.
	Presets.Add(TEXT("Dawn"), MakePreset(FRotator(-4.f, 85.f, 0.f), FLinearColor(1.f, 0.78f, 0.62f), 3.5f, 0.5f, FLinearColor(0.78f, 0.68f, 0.88f), 0.014f));
}

void ALSTimeOfDayDirector::BeginPlay()
{
	Super::BeginPlay();
	FindLights();
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnTimeOfDayChanged.AddUniqueDynamic(this, &ALSTimeOfDayDirector::HandleTimeOfDay);
		ApplyTimeOfDay(Story->GetTimeOfDay(), true);
	}
}

void ALSTimeOfDayDirector::FindLights()
{
	for (TActorIterator<ADirectionalLight> It(GetWorld()); It && !Sun.IsValid(); ++It) { Sun = *It; }
	for (TActorIterator<ASkyLight> It(GetWorld()); It && !Sky.IsValid(); ++It) { Sky = *It; }
	for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It && !Fog.IsValid(); ++It) { Fog = *It; }

	// The director owns a moon light and an unbound post-process volume for exposure.
	FActorSpawnParameters Params;
	Params.Owner = this;
	Moon = GetWorld()->SpawnActor<ADirectionalLight>(FVector(0.f, 0.f, 6000.f), FRotator(-40.f, 200.f, 0.f), Params);
	if (Moon)
	{
		UDirectionalLightComponent* L = CastChecked<UDirectionalLightComponent>(Moon->GetLightComponent());
		L->SetMobility(EComponentMobility::Movable);
		L->SetAtmosphereSunLight(false);
		L->SetIntensity(0.f);
	}
	Exposure = GetWorld()->SpawnActor<APostProcessVolume>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
	if (Exposure)
	{
		Exposure->bUnbound = true;
		Exposure->Priority = -10.f;
		Exposure->Settings.bOverride_AutoExposureBias = true;
		Exposure->Settings.AutoExposureBias = 0.f;
	}
	if (const ADirectionalLight* S = Sun.Get())
	{
		if (S->GetRootComponent()->Mobility != EComponentMobility::Movable)
		{
			UE_LOG(LogTemp, Warning, TEXT("Time of day: the sun '%s' is not Movable, so it cannot turn. Set its mobility to Movable."), *S->GetName());
		}
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("Time of day: no directional light in the level"));
	}
}

FLSTimeOfDayPreset ALSTimeOfDayDirector::Capture() const
{
	FLSTimeOfDayPreset P = To;
	if (const ADirectionalLight* S = Sun.Get())
	{
		P.SunRotation = S->GetActorRotation();
		P.SunColor = S->GetLightComponent()->GetLightColor();
		P.SunIntensity = S->GetLightComponent()->Intensity;
	}
	if (const ASkyLight* K = Sky.Get())
	{
		P.SkyIntensity = K->GetLightComponent()->Intensity;
	}
	if (const AExponentialHeightFog* F = Fog.Get())
	{
		P.FogColor = F->GetComponent()->FogInscatteringLuminance;
		P.FogDensity = F->GetComponent()->FogDensity;
	}
	if (const ADirectionalLight* M = Moon.Get())
	{
		P.MoonRotation = M->GetActorRotation();
		P.MoonIntensity = M->GetLightComponent()->Intensity;
		P.MoonColor = M->GetLightComponent()->GetLightColor();
	}
	if (const APostProcessVolume* E = Exposure.Get())
	{
		P.ExposureBias = E->Settings.AutoExposureBias;
	}
	return P;
}

void ALSTimeOfDayDirector::Apply(const FLSTimeOfDayPreset& P)
{
	if (ADirectionalLight* S = Sun.Get())
	{
		S->SetActorRotation(P.SunRotation);
		S->GetLightComponent()->SetLightColor(P.SunColor);
		S->GetLightComponent()->SetIntensity(P.SunIntensity);
	}
	if (ASkyLight* K = Sky.Get())
	{
		K->GetLightComponent()->SetIntensity(P.SkyIntensity);
	}
	if (AExponentialHeightFog* F = Fog.Get())
	{
		F->GetComponent()->SetFogInscatteringColor(P.FogColor);
		F->GetComponent()->SetFogDensity(P.FogDensity);
	}
	if (ADirectionalLight* M = Moon.Get())
	{
		M->SetActorRotation(P.MoonRotation);
		M->GetLightComponent()->SetLightColor(P.MoonColor);
		M->GetLightComponent()->SetIntensity(P.MoonIntensity);
	}
	if (APostProcessVolume* E = Exposure.Get())
	{
		E->Settings.AutoExposureBias = P.ExposureBias;
	}
}

void ALSTimeOfDayDirector::ApplyTimeOfDay(FName TimeOfDay, bool bInstant)
{
	const FLSTimeOfDayPreset* Preset = Presets.Find(TimeOfDay);
	if (!Preset)
	{
		UE_LOG(LogTemp, Warning, TEXT("Time of day '%s' has no lighting preset"), *TimeOfDay.ToString());
		return;
	}
	Current = TimeOfDay;
	From = Capture();
	To = *Preset;
	BlendAlpha = bInstant || BlendTime <= 0.f ? 1.f : 0.f;
	if (bInstant)
	{
		Apply(To);
	}
	UE_LOG(LogTemp, Display, TEXT("LS_TOD %s (sun pitch %.0f, %.1f lux)"), *TimeOfDay.ToString(), To.SunRotation.Pitch, To.SunIntensity);
}

void ALSTimeOfDayDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (BlendAlpha >= 1.f)
	{
		return;
	}
	BlendAlpha = FMath::Min(1.f, BlendAlpha + DeltaSeconds / BlendTime);
	const float A = FMath::SmoothStep(0.f, 1.f, BlendAlpha);
	FLSTimeOfDayPreset P;
	P.SunRotation = FMath::Lerp(From.SunRotation, To.SunRotation, A);
	P.SunColor = FMath::Lerp(From.SunColor, To.SunColor, A);
	P.SunIntensity = FMath::Lerp(From.SunIntensity, To.SunIntensity, A);
	P.SkyIntensity = FMath::Lerp(From.SkyIntensity, To.SkyIntensity, A);
	P.FogColor = FMath::Lerp(From.FogColor, To.FogColor, A);
	P.FogDensity = FMath::Lerp(From.FogDensity, To.FogDensity, A);
	P.MoonRotation = FMath::Lerp(From.MoonRotation, To.MoonRotation, A);
	P.MoonColor = FMath::Lerp(From.MoonColor, To.MoonColor, A);
	P.MoonIntensity = FMath::Lerp(From.MoonIntensity, To.MoonIntensity, A);
	P.ExposureBias = FMath::Lerp(From.ExposureBias, To.ExposureBias, A);
	Apply(P);
}

void ALSTimeOfDayDirector::HandleTimeOfDay(FName TimeOfDay)
{
	ApplyTimeOfDay(TimeOfDay, false);
}

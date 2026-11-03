// The Last Skyfarer: player settings.

#include "LSSettings.h"

#include "AudioDevice.h"
#include "DynamicRHI.h"
#include "Engine/World.h"
#include "GameFramework/GameUserSettings.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "RHI.h"

#define LOCTEXT_NAMESPACE "LSSettings"

namespace
{
	void SetCVar(const TCHAR* Name, int32 Value)
	{
		if (IConsoleVariable* V = IConsoleManager::Get().FindConsoleVariable(Name))
		{
			V->Set(Value, ECVF_SetByCode);
		}
	}
}

FText ULSSettings::QualityName(int32 Level)
{
	switch (Level)
	{
	case 0: return LOCTEXT("Low", "Low");
	case 1: return LOCTEXT("Medium", "Medium");
	case 2: return LOCTEXT("High", "High");
	default: return LOCTEXT("Epic", "Epic");
	}
}

int32 ULSSettings::DetectQuality()
{
	const FString Adapter = GRHIAdapterName;
	const bool bIntegrated = (GRHIVendorId == 0x8086 && !Adapter.Contains(TEXT("Arc"))) || Adapter.Contains(TEXT("UHD Graphics"))
		|| Adapter.Contains(TEXT("HD Graphics")) || Adapter.Contains(TEXT("Iris"));
	// The fallback to DirectX 11 means the GPU cannot run the default SM6 renderer well.
	const bool bFallbackRHI = GMaxRHIFeatureLevel < ERHIFeatureLevel::SM6;
	int32 Level = 3;
	if (bIntegrated || bFallbackRHI)
	{
		Level = 0;
	}
	else if (UGameUserSettings* GUS = UGameUserSettings::GetGameUserSettings())
	{
		GUS->RunHardwareBenchmark();
		Level = FMath::Clamp(GUS->ScalabilityQuality.GetMinQualityLevel(), 0, 3);
	}
	UE_LOG(LogTemp, Display, TEXT("LS_SETTINGS detected graphics preset %s for '%s' (integrated %d, feature level SM6 %d)"),
		*QualityName(Level).ToString(), *Adapter, bIntegrated ? 1 : 0, bFallbackRHI ? 0 : 1);
	return Level;
}

int32 ULSSettings::GetEffectiveQuality() const
{
	int32 Override = -1;
	if (FParse::Value(FCommandLine::Get(), TEXT("LSQuality="), Override) && Override >= 0)
	{
		return FMath::Clamp(Override, 0, 3);
	}
	return FMath::Clamp(Quality, 0, 3);
}

void ULSSettings::SaveAndApply(const UObject* WorldContext)
{
	SaveConfig();
	Apply(WorldContext);
}

void ULSSettings::Apply(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (FAudioDeviceHandle Device = World ? World->GetAudioDevice() : FAudioDeviceHandle())
	{
		Device->SetTransientPrimaryVolume(MasterVolume);
	}

	if (Quality < 0)
	{
		Quality = DetectQuality();
		if (Quality == 0)
		{
			ResolutionScale = 50; // integrated graphics are fill-rate bound: render the 3D view at half size and scale it up
			FrameCap = 30;        // and a steady 30 fps leaves the GPU headroom instead of running flat out
		}
		SaveConfig();
	}
	const int32 Level = GetEffectiveQuality();
	if (UGameUserSettings* GUS = UGameUserSettings::GetGameUserSettings())
	{
		GUS->SetOverallScalabilityLevel(Level);
		GUS->SetVSyncEnabled(bVSync);
		GUS->SetFrameRateLimit(FrameCap > 0 ? static_cast<float>(FrameCap) : 0.f);
		GUS->ApplyNonResolutionSettings();
	}
	SetCVar(TEXT("r.ScreenPercentage"), FMath::Clamp(ResolutionScale, 50, 100));

	// Low trades Lumen, virtual shadow maps, volumetric fog and clouds and distance-field shadows for the sky light,
	// regular shadow maps, height fog and the plain sky,
	// which keeps integrated graphics (like the Intel UHD 630) from timing out.
	const bool bLow = Level == 0;
	SetCVar(TEXT("r.DynamicGlobalIlluminationMethod"), bLow ? 0 : 1);
	SetCVar(TEXT("r.ReflectionMethod"), bLow ? 2 : 1);
	SetCVar(TEXT("r.Shadow.Virtual.Enable"), bLow ? 0 : 1);
	SetCVar(TEXT("r.VolumetricFog"), bLow ? 0 : 1);
	SetCVar(TEXT("r.VolumetricCloud"), bLow ? 0 : 1);
	SetCVar(TEXT("r.DistanceFieldShadowing"), bLow ? 0 : 1);
	SetCVar(TEXT("r.DistanceFieldAO"), bLow ? 0 : 1);
	// GPU timeouts on the Intel UHD 630 (DirectX 11) were reported while creating occlusion queries; the greybox is
	// cheap to draw without occlusion culling.
	SetCVar(TEXT("r.AllowOcclusionQueries"), bLow ? 0 : 1);
	UE_LOG(LogTemp, Display, TEXT("LS_SETTINGS graphics %s, %d%% resolution, vsync %d, cap %d"), *QualityName(Level).ToString(), ResolutionScale, bVSync ? 1 : 0, FrameCap);
}

#undef LOCTEXT_NAMESPACE

// The Last Skyfarer: map bounds and top-down capture.

#include "LSMapBounds.h"

#include "Components/BoxComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"

ALSMapBounds::ALSMapBounds()
{
	PrimaryActorTick.bCanEverTick = false;

	Bounds = CreateDefaultSubobject<UBoxComponent>(TEXT("Bounds"));
	RootComponent = Bounds;
	Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Bounds->SetBoxExtent(FVector(80000.f, 80000.f, 20000.f));
	Bounds->ShapeColor = FColor(200, 170, 90);

	Capture = CreateDefaultSubobject<USceneCaptureComponent2D>(TEXT("Capture"));
	Capture->SetupAttachment(Bounds);
	Capture->ProjectionType = ECameraProjectionMode::Orthographic;
	Capture->bCaptureEveryFrame = false;
	Capture->bCaptureOnMovement = false;
	Capture->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
	// Looking straight down with north (+X) at the top of the image.
	Capture->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f));
	// A drawn map needs no expensive lighting: skip Lumen, fog, clouds, shadows and post effects, so the one-off
	// capture stays cheap even on integrated graphics.
	Capture->ShowFlags.SetLumenGlobalIllumination(false);
	Capture->ShowFlags.SetLumenReflections(false);
	Capture->ShowFlags.SetFog(false);
	Capture->ShowFlags.SetVolumetricFog(false);
	Capture->ShowFlags.SetCloud(false);
	Capture->ShowFlags.SetDynamicShadows(false);
	Capture->ShowFlags.SetAmbientOcclusion(false);
	Capture->ShowFlags.SetBloom(false);
	Capture->ShowFlags.SetMotionBlur(false);
	Capture->ShowFlags.SetAntiAliasing(false);
}

void ALSMapBounds::BeginPlay()
{
	Super::BeginPlay();
	MapImage = NewObject<UTextureRenderTarget2D>(this);
	MapImage->InitAutoFormat(ImageSize, ImageSize);
	MapImage->UpdateResourceImmediate(true);
	Capture->TextureTarget = MapImage;
	Capture->OrthoWidth = HalfSide() * 2.f;
	Capture->SetRelativeLocation(FVector(0.f, 0.f, Bounds->GetScaledBoxExtent().Z));

	FTimerHandle Handle;
	GetWorldTimerManager().SetTimer(Handle, this, &ALSMapBounds::CaptureNow, FMath::Max(CaptureDelay, 0.05f), false);
}

void ALSMapBounds::CaptureNow()
{
	if (Capture && MapImage)
	{
		Capture->CaptureScene();
		bCaptured = true;
	}
}

float ALSMapBounds::HalfSide() const
{
	const FVector E = Bounds->GetScaledBoxExtent();
	return FMath::Max(E.X, E.Y);
}

FVector2D ALSMapBounds::WorldToMap(const FVector& World) const
{
	const FVector C = Bounds->GetComponentLocation();
	const float H = HalfSide();
	// Image x grows east (+Y); image y grows south (-X).
	return FVector2D((World.Y - C.Y + H) / (2.f * H), (C.X + H - World.X) / (2.f * H));
}

FVector ALSMapBounds::MapToWorld(const FVector2D& Map, float Z) const
{
	const FVector C = Bounds->GetComponentLocation();
	const float H = HalfSide();
	return FVector(C.X + H - Map.Y * 2.f * H, C.Y - H + Map.X * 2.f * H, Z);
}

ALSMapBounds* ALSMapBounds::Find(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (World)
	{
		for (TActorIterator<ALSMapBounds> It(World); It; ++It)
		{
			return *It;
		}
	}
	return nullptr;
}

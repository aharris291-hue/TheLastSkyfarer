// The Last Skyfarer: the area a level's map covers, plus a top-down capture used as the map image.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSMapBounds.generated.h"

class UBoxComponent;
class USceneCaptureComponent2D;
class UTextureRenderTarget2D;

/**
 * Place one per level. The box sets what the map shows (north = +X at the top, east = +Y to the right).
 * At play start it renders the level once from above into MapImage (placeholder until the inked map art).
 */
UCLASS()
class LASTSKYFARER_API ALSMapBounds : public AActor
{
	GENERATED_BODY()

public:
	ALSMapBounds();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Map")
	TObjectPtr<UBoxComponent> Bounds;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Map")
	TObjectPtr<USceneCaptureComponent2D> Capture;

	/** Map name shown in the corner. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	FText MapTitle;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	int32 ImageSize = 1024;

	/** Seconds after play starts to take the capture (lets lighting settle). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Map")
	float CaptureDelay = 1.f;

	UFUNCTION(BlueprintPure, Category = "Map")
	UTextureRenderTarget2D* GetMapImage() const { return MapImage; }

	/** 0..1 across the square map area: X = east, Y = south (image space). */
	UFUNCTION(BlueprintPure, Category = "Map")
	FVector2D WorldToMap(const FVector& World) const;

	UFUNCTION(BlueprintPure, Category = "Map")
	FVector MapToWorld(const FVector2D& Map, float Z = 0.f) const;

	/** The first map bounds in the world, if any. */
	static ALSMapBounds* Find(const UObject* WorldContext);

	UFUNCTION(BlueprintCallable, Category = "Map")
	void CaptureNow();

	/** Captures only if the map image has not been drawn yet (the island does not change while playing). */
	UFUNCTION(BlueprintCallable, Category = "Map")
	void CaptureIfNeeded() { if (!bCaptured) { CaptureNow(); } }

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UTextureRenderTarget2D> MapImage;

	/** Half the side of the square the map covers, cm. */
	float HalfSide() const;
private:
	bool bCaptured = false;
};

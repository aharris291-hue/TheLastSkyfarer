// The Last Skyfarer: Piko, Kieran's companion (GDD 5). Non-verbal through Acts I-II (D-12).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PikoCompanion.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

UENUM(BlueprintType)
enum class EPikoPerch : uint8
{
	/** Floating behind Kieran's shoulder. */
	Follow,
	/** Sitting on the shoulder (idle in town). */
	Shoulder,
	/** Riding the glider crossbar. */
	GliderBar,
	/** Asleep in the satchel (long dialogue). */
	Satchel
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnPikoSensed, int32, NumRevealed);

UCLASS(Blueprintable)
class LASTSKYFARER_API APikoCompanion : public AActor
{
	GENERATED_BODY()

public:
	APikoCompanion();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Piko")
	TObjectPtr<UStaticMeshComponent> Body;

	/** The character Piko follows; found automatically (player 0) if empty. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko")
	TObjectPtr<AActor> FollowTarget;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko")
	EPikoPerch Perch = EPikoPerch::Follow;

	/** Offset from the target in its local space while following, cm (behind, right shoulder, above). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Follow")
	FVector FollowOffset = FVector(-120.f, 60.f, 80.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Follow")
	FVector ShoulderOffset = FVector(0.f, 22.f, 70.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Follow")
	FVector GliderBarOffset = FVector(40.f, 0.f, 110.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Follow")
	FVector SatchelOffset = FVector(-5.f, -25.f, -10.f);

	/** Spring stiffness (critically damped). Higher = snappier. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Follow", meta = (ClampMin = "0.1"))
	float SpringStiffness = 6.f;

	/** Snap to the target if further than this, cm (e.g. after a teleport). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Follow")
	float TeleportDistance = 3000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Idle")
	float BobAmplitude = 8.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Idle")
	float BobFrequency = 0.8f;

	/** Range for sensing hidden currents, cm (40 m). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Sense")
	float SenseRange = 4000.f;

	/** Markings start to glow when a hidden current is this close, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Sense")
	float GlowRange = 6000.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Sense")
	float SenseInterval = 0.25f;

	/** Material scalar parameter driven by MarkingGlow. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Piko|Sense")
	FName MarkingGlowParam = TEXT("MarkingGlow");

	/** 0..1, rises as a hidden current gets closer and pulses after a reveal. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Piko|Sense")
	float MarkingGlow = 0.f;

	UPROPERTY(BlueprintAssignable, Category = "Piko")
	FOnPikoSensed OnSensedCurrent;

	/** Looks for hidden currents within SenseRange; reveals them. Returns how many were revealed. */
	UFUNCTION(BlueprintCallable, Category = "Piko")
	int32 Sense();

	UFUNCTION(BlueprintCallable, Category = "Piko")
	void SetPerch(EPikoPerch NewPerch) { Perch = NewPerch; }

	/** Where Piko wants to be right now (before bob). */
	UFUNCTION(BlueprintPure, Category = "Piko")
	FVector GetDesiredLocation() const;

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> BodyMaterial;

	FVector Velocity = FVector::ZeroVector;
	float SenseTimer = 0.f;
	float RevealPulse = 0.f;
	float BobTime = 0.f;
};

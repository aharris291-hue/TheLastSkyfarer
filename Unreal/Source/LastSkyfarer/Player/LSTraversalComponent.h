// The Last Skyfarer: mantle, ledge hang and shimmy, and climbing (GDD 1).

#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LSTraversalComponent.generated.h"

class ACharacter;

UENUM(BlueprintType)
enum class ETraversalState : uint8
{
	None,
	Mantling,
	Hanging,
	Climbing
};

/** A ledge found in front of the character. */
USTRUCT(BlueprintType)
struct FLSLedge
{
	GENERATED_BODY()

	/** Point on top of the ledge, just past the wall edge. */
	UPROPERTY(BlueprintReadOnly, Category = "Traversal")
	FVector Top = FVector::ZeroVector;

	/** Wall surface point and outward normal (horizontal). */
	UPROPERTY(BlueprintReadOnly, Category = "Traversal")
	FVector WallPoint = FVector::ZeroVector;

	UPROPERTY(BlueprintReadOnly, Category = "Traversal")
	FVector WallNormal = FVector::ZeroVector;

	/** Ledge top height above the character's feet, cm. */
	UPROPERTY(BlueprintReadOnly, Category = "Traversal")
	float Height = 0.f;

	/** The wall is tagged Climbable. */
	UPROPERTY(BlueprintReadOnly, Category = "Traversal")
	bool bClimbable = false;

	/** There is a standable top with room for the capsule. */
	UPROPERTY(BlueprintReadOnly, Category = "Traversal")
	bool bHasTop = false;
};

/**
 * Traversal moves on top of the Character Movement Component. While mantling, hanging or
 * climbing the character is in MOVE_Flying and this component moves it directly.
 * Climbable surfaces carry the actor or component tag "Climbable".
 */
UCLASS(ClassGroup = (LastSkyfarer), meta = (BlueprintSpawnableComponent))
class LASTSKYFARER_API ULSTraversalComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	ULSTraversalComponent();

	/** Obstacles from this height (cm above the feet)... */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Mantle")
	float MinMantleHeight = 50.f;

	/** ...up to this height are mantled automatically while moving into them. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Mantle")
	float MaxMantleHeight = 180.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Mantle")
	float MantleDuration = 0.45f;

	/** While falling, ledges up to this height above the feet are grabbed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Hang")
	float MaxHangReach = 230.f;

	/** Ledge height above the feet while hanging, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Hang")
	float HangHeight = 200.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Hang")
	float ShimmySpeed = 100.f;

	/** GDD: 1.2 m/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Climb")
	float ClimbSpeed = 120.f;

	/** GDD: jump while climbing hops 1.5 m. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Climb")
	float ClimbHopDistance = 150.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal|Climb")
	FName ClimbableTag = TEXT("Climbable");

	/** How far in front of the capsule to look for walls, cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal")
	float WallReach = 45.f;

	/** No re-grab for this long after dropping or jumping off, s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Traversal")
	float RegrabCooldown = 0.4f;

	UFUNCTION(BlueprintPure, Category = "Traversal")
	ETraversalState GetState() const { return State; }

	UFUNCTION(BlueprintPure, Category = "Traversal")
	bool IsBusy() const { return State != ETraversalState::None; }

	/** Desired move direction in world space (for detection), and raw stick (for hang/climb). */
	void SetMoveInput(const FVector& WorldDirection, float Right, float Forward);

	/** Jump pressed while busy: hang -> pull up, climb -> hop. Returns true if consumed. */
	bool Jump();

	/** Let go (Ctrl / B). */
	void Drop();

	/** What to do with a ledge found in front (pure decision; used by TryEnter and tests). */
	ETraversalState Classify(const FLSLedge& Ledge, bool bFalling, bool bPushing, float VerticalSpeed) const;

	/** Looks for a ledge in front, in the given horizontal direction. */
	bool FindLedge(const FVector& Direction, FLSLedge& Out) const;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<ACharacter> Character;

	ETraversalState State = ETraversalState::None;
	FVector MoveDir = FVector::ZeroVector;
	float StickRight = 0.f;
	float StickForward = 0.f;
	double CooldownUntil = -1.0;
	bool bAutoRegrab = false;

	// Mantle path.
	FVector MantleStart = FVector::ZeroVector;
	FVector MantleMid = FVector::ZeroVector;
	FVector MantleEnd = FVector::ZeroVector;
	float MantleTime = 0.f;
	float MantleLength = 0.f;

	FVector WallNormal = FVector::ZeroVector;

	double Now() const;
	float FeetZ() const;
	bool TraceWall(const FVector& From, const FVector& Direction, FHitResult& Hit) const;
	bool CapsuleFits(const FVector& Location) const;
	void SetFlying();
	void EndTraversal(EMovementMode Mode);

	void TryEnter();
	void StartMantle(const FLSLedge& Ledge);
	void StartHang(const FLSLedge& Ledge);
	void StartClimb(const FHitResult& Wall);
	void TickMantle(float Dt);
	void TickHang(float Dt);
	void TickClimb(float Dt);
};

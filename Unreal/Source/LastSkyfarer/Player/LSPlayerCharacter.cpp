// The Last Skyfarer: Kieran, the player character (GDD 1 and 2).

#include "LSPlayerCharacter.h"

#include "Animation/AnimInstance.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "GliderComponent.h"
#include "LSTraversalComponent.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "UObject/ConstructorHelpers.h"

ALSPlayerCharacter::ALSPlayerCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	Glider = CreateDefaultSubobject<UGliderComponent>(TEXT("Glider"));
	Traversal = CreateDefaultSubobject<ULSTraversalComponent>(TEXT("Traversal"));

	// Template input actions and placeholder mannequin, so the class works without a Blueprint child.
	static ConstructorHelpers::FObjectFinder<UInputAction> MoveIA(TEXT("/Game/Input/Actions/IA_Move.IA_Move"));
	static ConstructorHelpers::FObjectFinder<UInputAction> LookIA(TEXT("/Game/Input/Actions/IA_Look.IA_Look"));
	static ConstructorHelpers::FObjectFinder<UInputAction> MouseLookIA(TEXT("/Game/Input/Actions/IA_MouseLook.IA_MouseLook"));
	static ConstructorHelpers::FObjectFinder<UInputAction> JumpIA(TEXT("/Game/Input/Actions/IA_Jump.IA_Jump"));
	if (MoveIA.Succeeded()) { MoveAction = MoveIA.Object; }
	if (LookIA.Succeeded()) { LookAction = LookIA.Object; }
	if (MouseLookIA.Succeeded()) { MouseLookAction = MouseLookIA.Object; }
	if (JumpIA.Succeeded()) { JumpAction = JumpIA.Object; }

	static ConstructorHelpers::FObjectFinder<USkeletalMesh> MeshAsset(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple"));
	static ConstructorHelpers::FClassFinder<UAnimInstance> AnimClass(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"));
	if (MeshAsset.Succeeded())
	{
		GetMesh()->SetSkeletalMesh(MeshAsset.Object);
		GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -96.f), FRotator(0.f, -90.f, 0.f));
	}
	if (AnimClass.Succeeded())
	{
		GetMesh()->SetAnimInstanceClass(AnimClass.Class);
	}

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->MaxWalkSpeed = RunSpeed;
	Move->JumpZVelocity = FMath::Sqrt(2.f * 980.f * JumpHeight);
	Move->AirControl = 0.4f;

	GetCameraBoom()->TargetArmLength = CameraDistance;
	GetCameraBoom()->SocketOffset = FVector(0.f, CameraShoulderOffset, 40.f);
	GetFollowCamera()->FieldOfView = BaseFOV;
}

double ALSPlayerCharacter::Now() const
{
	return GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
}

void ALSPlayerCharacter::BeginPlay()
{
	Super::BeginPlay();
	const float Gravity = FMath::Abs(GetCharacterMovement()->GetGravityZ());
	GetCharacterMovement()->JumpZVelocity = FMath::Sqrt(2.f * (Gravity > 0.f ? Gravity : 980.f) * JumpHeight);
	SafePoints.SampleInterval = SafePointInterval;
	SampleSafePoint(Now(), true);
	UpdateSpeed();
}

void ALSPlayerCharacter::EnsureExtraInput()
{
	auto MakeAction = [this](const TCHAR* Name) -> UInputAction*
	{
		UInputAction* A = NewObject<UInputAction>(this, Name);
		A->ValueType = EInputActionValueType::Boolean;
		return A;
	};
	if (!SprintAction) { SprintAction = MakeAction(TEXT("IA_Sprint_Runtime")); }
	if (!WalkToggleAction) { WalkToggleAction = MakeAction(TEXT("IA_WalkToggle_Runtime")); }
	if (!AirBrakeAction) { AirBrakeAction = MakeAction(TEXT("IA_AirBrake_Runtime")); }

	if (!ExtraMappingContext)
	{
		ExtraMappingContext = NewObject<UInputMappingContext>(this, TEXT("IMC_LSPlayer_Runtime"));
		ExtraMappingContext->MapKey(SprintAction, EKeys::LeftShift);
		ExtraMappingContext->MapKey(SprintAction, EKeys::Gamepad_LeftThumbstick);
		ExtraMappingContext->MapKey(WalkToggleAction, EKeys::LeftControl);
		ExtraMappingContext->MapKey(AirBrakeAction, EKeys::LeftControl);
		ExtraMappingContext->MapKey(AirBrakeAction, EKeys::Gamepad_FaceButton_Right);
	}
}

void ALSPlayerCharacter::NotifyControllerChanged()
{
	Super::NotifyControllerChanged();
	EnsureExtraInput();
	if (const APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			if (!Sub->HasMappingContext(ExtraMappingContext))
			{
				Sub->AddMappingContext(ExtraMappingContext, 1);
			}
		}
	}
}

void ALSPlayerCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	// Bind everything here instead of in the template, so Jump goes through DoJumpStart (coyote, buffer, glider).
	ACharacter::SetupPlayerInputComponent(PlayerInputComponent);
	EnsureExtraInput();

	if (UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(PlayerInputComponent))
	{
		EIC->BindAction(JumpAction, ETriggerEvent::Started, this, &ALSPlayerCharacter::DoJumpStart);
		EIC->BindAction(JumpAction, ETriggerEvent::Completed, this, &ALSPlayerCharacter::DoJumpEnd);
		EIC->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ALSPlayerCharacter::Move);
		EIC->BindAction(MoveAction, ETriggerEvent::Completed, this, &ALSPlayerCharacter::Move);
		EIC->BindAction(LookAction, ETriggerEvent::Triggered, this, &ALSPlayerCharacter::Look);
		EIC->BindAction(MouseLookAction, ETriggerEvent::Triggered, this, &ALSPlayerCharacter::Look);
		EIC->BindAction(SprintAction, ETriggerEvent::Started, this, &ALSPlayerCharacter::StartSprint);
		EIC->BindAction(SprintAction, ETriggerEvent::Completed, this, &ALSPlayerCharacter::StopSprint);
		EIC->BindAction(WalkToggleAction, ETriggerEvent::Started, this, &ALSPlayerCharacter::ToggleWalk);
		EIC->BindAction(AirBrakeAction, ETriggerEvent::Started, this, &ALSPlayerCharacter::AirBrakePressed);
		EIC->BindAction(AirBrakeAction, ETriggerEvent::Completed, this, &ALSPlayerCharacter::AirBrakeReleased);
	}
}

void ALSPlayerCharacter::DoMove(float Right, float Forward)
{
	if (Glider && Glider->IsGliding())
	{
		// Stick forward dives, back pulls up; left/right banks.
		Glider->SetControlInput(Right, Forward);
		return;
	}
	if (Traversal)
	{
		const FRotator Yaw(0.f, GetControlRotation().Yaw, 0.f);
		const FVector WorldDir = FRotationMatrix(Yaw).GetUnitAxis(EAxis::X) * Forward + FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y) * Right;
		Traversal->SetMoveInput(WorldDir, Right, Forward);
		if (Traversal->IsBusy())
		{
			return;
		}
	}
	Super::DoMove(Right, Forward);
}

void ALSPlayerCharacter::DoJumpStart()
{
	UCharacterMovementComponent* Move = GetCharacterMovement();
	if (Traversal && Traversal->Jump())
	{
		return;
	}
	if (Glider && Glider->IsGliding())
	{
		Glider->Stow();
		return;
	}
	if (Move->IsFalling())
	{
		if (!bJumpedSinceGrounded && Now() - LeftGroundTime <= CoyoteTime)
		{
			// Coyote jump: just walked off an edge.
			bJumpedSinceGrounded = true;
			LaunchCharacter(FVector(0.f, 0.f, Move->JumpZVelocity), false, true);
			return;
		}
		if (Glider && Glider->TryDeploy())
		{
			return;
		}
		JumpPressedTime = Now();
		return;
	}
	bJumpedSinceGrounded = true;
	Super::DoJumpStart();
}

void ALSPlayerCharacter::DoJumpEnd()
{
	Super::DoJumpEnd();
}

void ALSPlayerCharacter::Landed(const FHitResult& Hit)
{
	Super::Landed(Hit);
	bJumpedSinceGrounded = false;
	if (Now() - JumpPressedTime <= JumpBufferTime)
	{
		JumpPressedTime = -100.0;
		bJumpedSinceGrounded = true;
		Jump();
	}
}

void ALSPlayerCharacter::OnMovementModeChanged(EMovementMode PrevMovementMode, uint8 PreviousCustomMode)
{
	Super::OnMovementModeChanged(PrevMovementMode, PreviousCustomMode);
	const EMovementMode Mode = GetCharacterMovement()->MovementMode;
	if (PrevMovementMode == MOVE_Walking && Mode == MOVE_Falling)
	{
		LeftGroundTime = Now();
	}
	if (Mode == MOVE_Walking)
	{
		bJumpedSinceGrounded = false;
	}
}

void ALSPlayerCharacter::StartSprint()
{
	if (Now() - SprintEndTime < SprintCooldown)
	{
		return;
	}
	bSprinting = true;
	bWalkMode = false;
	SprintStartTime = Now();
	UpdateSpeed();
}

void ALSPlayerCharacter::StopSprint()
{
	if (bSprinting)
	{
		bSprinting = false;
		SprintEndTime = Now();
		UpdateSpeed();
	}
}

void ALSPlayerCharacter::ToggleWalk()
{
	if (Traversal && Traversal->IsBusy())
	{
		Traversal->Drop();
		return;
	}
	if (Glider && Glider->IsGliding())
	{
		return;
	}
	bWalkMode = !bWalkMode;
	UpdateSpeed();
}

void ALSPlayerCharacter::AirBrakePressed()
{
	if (Traversal && Traversal->IsBusy())
	{
		Traversal->Drop();
		return;
	}
	if (Glider) { Glider->SetAirBrake(true); }
}

void ALSPlayerCharacter::AirBrakeReleased()
{
	if (Glider) { Glider->SetAirBrake(false); }
}

void ALSPlayerCharacter::UpdateSpeed()
{
	GetCharacterMovement()->MaxWalkSpeed = bSprinting ? SprintSpeed : (bWalkMode ? WalkSpeed : RunSpeed);
}

namespace
{
	// Moving platforms are never a safe point.
	bool IsOnMovingFloor(const UCharacterMovementComponent* Move)
	{
		const UPrimitiveComponent* Floor = Move->CurrentFloor.HitResult.GetComponent();
		return Floor && Floor->Mobility == EComponentMobility::Movable;
	}
}

void ALSPlayerCharacter::SampleSafePoint(double Time, bool bForceStable)
{
	const UCharacterMovementComponent* Move = GetCharacterMovement();
	const bool bStable = bForceStable ||
		(Move->IsMovingOnGround() && Move->CurrentFloor.IsWalkableFloor() && !IsOnMovingFloor(Move));
	SafePoints.SampleInterval = SafePointInterval;
	SafePoints.Update(Time, GetActorLocation(), bStable);
}

bool ALSPlayerCharacter::CheckRecovery()
{
	if (GetActorLocation().Z < RecoveryZ)
	{
		RecoverToSafePoint();
		return true;
	}
	return false;
}

void ALSPlayerCharacter::RecoverToSafePoint()
{
	if (Glider)
	{
		Glider->Stow();
	}
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->StopMovementImmediately();
	SetActorLocation(SafePoints.bHasSafePoint ? SafePoints.SafePoint : GetActorLocation(), false, nullptr, ETeleportType::TeleportPhysics);
	Move->SetMovementMode(MOVE_Falling);
}

void ALSPlayerCharacter::UpdateCamera(float DeltaSeconds)
{
	const bool bGliding = Glider && Glider->IsGliding();
	const float Alpha = bGliding
		? FMath::GetMappedRangeValueClamped(FVector2D(Glider->Params.TrimSpeed * 0.5f, Glider->Params.MaxDiveSpeed), FVector2D(0.4f, 1.f), Glider->GetAirspeed())
		: 0.f;
	const float TargetArm = FMath::Lerp(CameraDistance, CameraGlideDistance, Alpha);
	const float TargetFOV = FMath::Lerp(BaseFOV, MaxGlideFOV, Alpha);
	GetCameraBoom()->TargetArmLength = FMath::FInterpTo(GetCameraBoom()->TargetArmLength, TargetArm, DeltaSeconds, 3.f);
	GetFollowCamera()->FieldOfView = FMath::FInterpTo(GetFollowCamera()->FieldOfView, TargetFOV, DeltaSeconds, 3.f);
}

void ALSPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (bSprinting && Now() - SprintStartTime >= SprintDuration)
	{
		StopSprint();
	}
	SampleSafePoint(Now());
	CheckRecovery();
	UpdateCamera(DeltaSeconds);
}

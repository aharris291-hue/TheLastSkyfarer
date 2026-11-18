#include "LSBeacon.h"

#include "LSInteractableComponent.h"
#include "LSStorySubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 NumRingMeshes = 3;
}

ALSBeacon::ALSBeacon()
{
	PrimaryActorTick.bCanEverTick = true;

	Pillar = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Pillar"));
	RootComponent = Pillar;
	Pillar->SetRelativeScale3D(FVector(1.f, 1.f, 4.f));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cylinder.Succeeded()) Pillar->SetStaticMesh(Cylinder.Object);

	for (int32 i = 0; i < NumRingMeshes; ++i)
	{
		UStaticMeshComponent* Ring = CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("Ring%d"), i));
		Ring->SetupAttachment(RootComponent);
		Ring->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Ring->SetAbsolute(false, false, true);
		Ring->SetRelativeScale3D(FVector(2.f + i * 0.6f, 2.f + i * 0.6f, 0.05f));	// placeholder discs
		Ring->SetRelativeLocation(FVector(0.f, 0.f, 20.f + i * 12.f));
		if (Cylinder.Succeeded()) Ring->SetStaticMesh(Cylinder.Object);
		RingMeshes.Add(Ring);
	}

	Interactable = CreateDefaultSubobject<ULSInteractableComponent>(TEXT("Interactable"));
	Interactable->SetupAttachment(RootComponent);
	Interactable->Prompt = NSLOCTEXT("LS", "AlignRings", "Align the rings");
	Interactable->Radius = 400.f;
}

FName ALSBeacon::BeaconId() const
{
	return Definition ? Definition->Id : NAME_None;
}

void ALSBeacon::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	if (Definition) Puzzle.Reset(Definition->Rings);
}

void ALSBeacon::BeginPlay()
{
	Super::BeginPlay();
	if (Definition) Puzzle.Reset(Definition->Rings);
	RefreshInteractable();
	Interactable->OnInteracted.AddDynamic(this, &ALSBeacon::HandleInteracted);
}

void ALSBeacon::RefreshInteractable()
{
	FLSInteractionRule Rule;
	const FName Id = BeaconId();
	if (!Id.IsNone())
	{
		Rule.If = { ULSRestorationLibrary::StageFlag(Id, ELSRestorationStage::Restored).ToString(),
			TEXT("!") + ULSRestorationLibrary::StageFlag(Id, ELSRestorationStage::Synchronized).ToString() };
		Interactable->Rules = { Rule };
	}
	else
	{
		Interactable->Rules.Reset();
	}
}

ELSRestorationStage ALSBeacon::GetStage() const
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	return Story ? ULSRestorationLibrary::GetStage(*Story, BeaconId()) : ELSRestorationStage::Unknown;
}

bool ALSBeacon::AdvanceTo(ELSRestorationStage Stage)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story || !Definition) return false;
	if (!ULSRestorationLibrary::AdvanceTo(*Story, Definition->Id, Stage, &Definition->StageActions)) return false;
	OnStageChanged.Broadcast(Definition->Id, Stage);
	if (Stage == ELSRestorationStage::Synchronized) OnRegionalReaction.Broadcast(Definition->Id);
	return true;
}

void ALSBeacon::HandleInteracted(AActor*)
{
	BeginSynchronize();
}

bool ALSBeacon::BeginSynchronize()
{
	if (GetStage() != ELSRestorationStage::Restored || !Definition || Definition->Rings.Num() == 0) return false;
	Puzzle.Reset(Definition->Rings);
	bSynchronizing = true;
	return true;
}

void ALSBeacon::CancelSynchronize()
{
	bSynchronizing = false;	// positions are kept; no fail state
}

bool ALSBeacon::TurnRing(int32 Ring, int32 Direction)
{
	if (!bSynchronizing || !Puzzle.Rotate(Ring, Direction >= 0 ? 1 : -1)) return false;
	OnRingTurned.Broadcast(Ring, Puzzle.IsRingAligned(Ring));
	if (Puzzle.IsSolved())
	{
		bSynchronizing = false;
		AdvanceTo(ELSRestorationStage::Synchronized);
	}
	return true;
}

void ALSBeacon::FinishRegionalReaction()
{
	if (GetStage() != ELSRestorationStage::Synchronized) return;
	AdvanceTo(ELSRestorationStage::Reacted);
	AdvanceTo(ELSRestorationStage::Advanced);
}

void ALSBeacon::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	// Ease each ring towards the yaw of its current glyph.
	for (int32 i = 0; i < RingMeshes.Num() && i < Puzzle.Positions.Num(); ++i)
	{
		UStaticMeshComponent* Mesh = RingMeshes[i];
		const float Want = 360.f * Puzzle.Positions[i] / FMath::Max(Puzzle.Rings[i].NumGlyphs, 2);
		const FRotator Rot = Mesh->GetRelativeRotation();
		const float Delta = FMath::FindDeltaAngleDegrees(Rot.Yaw, Want);
		const float Step = FMath::Clamp(Delta, -RingTurnSpeed * DeltaTime, RingTurnSpeed * DeltaTime);
		Mesh->SetRelativeRotation(FRotator(Rot.Pitch, Rot.Yaw + Step, Rot.Roll));
	}
}

#include "LSStoryVolumes.h"
#include "TimerManager.h"

#include "LSInteractableComponent.h"
#include "LSStorySubsystem.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	bool IsPlayerPawn(const AActor* Other)
	{
		const APawn* Pawn = Cast<APawn>(Other);
		return Pawn && Pawn->IsPlayerControlled();
	}

	void SetupTriggerBox(UBoxComponent* Box, const FVector& Extent)
	{
		Box->SetBoxExtent(Extent);
		Box->SetCollisionProfileName(TEXT("Trigger"));
		Box->SetGenerateOverlapEvents(true);
		Box->ShapeColor = FColor(80, 180, 255);
	}
}

// ---------------------------------------------------------------- ALSStoryTrigger

ALSStoryTrigger::ALSStoryTrigger()
{
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	RootComponent = Box;
	SetupTriggerBox(Box, FVector(200.f, 200.f, 200.f));
}

void ALSStoryTrigger::BeginPlay()
{
	Super::BeginPlay();
	Box->OnComponentBeginOverlap.AddDynamic(this, &ALSStoryTrigger::HandleOverlap);
	// The player can spawn inside the box before this overlap is bound: check once the frame after.
	GetWorldTimerManager().SetTimerForNextTick([this]()
	{
		TArray<AActor*> Inside;
		Box->GetOverlappingActors(Inside);
		for (AActor* A : Inside) { if (IsPlayerPawn(A)) { TryFire(A); break; } }
	});
}

void ALSStoryTrigger::HandleOverlap(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	if (IsPlayerPawn(Other)) TryFire(Other);
}

bool ALSStoryTrigger::TryFire(AActor* Other)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story || OnceFlag.IsNone() || Story->HasFlag(OnceFlag) || !Story->CheckAll(Conditions)) return false;
	if (!Conversation.IsNone() && Story->IsInDialogue()) return false;	// try again on the next overlap

	Story->SetFlag(OnceFlag);
	Story->RunActions(Actions);
	if (!Conversation.IsNone()) Story->StartConversation(Conversation);
	return true;
}

// ---------------------------------------------------------------- ALSLocationVolume

ALSLocationVolume::ALSLocationVolume()
{
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	RootComponent = Box;
	SetupTriggerBox(Box, FVector(2000.f, 2000.f, 1500.f));
	Box->ShapeColor = FColor(255, 210, 90);
}

void ALSLocationVolume::BeginPlay()
{
	Super::BeginPlay();
	Box->OnComponentBeginOverlap.AddDynamic(this, &ALSLocationVolume::HandleOverlap);
	// Same as story triggers: a player who starts inside is discovered the frame after.
	GetWorldTimerManager().SetTimerForNextTick([this]()
	{
		TArray<AActor*> Inside;
		Box->GetOverlappingActors(Inside);
		for (AActor* A : Inside)
		{
			if (IsPlayerPawn(A) && !LocationId.IsNone())
			{
				if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this)) { Story->DiscoverLocation(LocationId); }
				break;
			}
		}
	});
}

void ALSLocationVolume::HandleOverlap(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	if (!IsPlayerPawn(Other) || LocationId.IsNone()) return;
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->DiscoverLocation(LocationId);
	}
}

// ---------------------------------------------------------------- ALSJournalPickup

ALSJournalPickup::ALSJournalPickup()
{
	PrimaryActorTick.bCanEverTick = true;

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetRelativeScale3D(FVector(0.3f, 0.22f, 0.02f));	// placeholder page
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded()) Mesh->SetStaticMesh(Cube.Object);

	Interactable = CreateDefaultSubobject<ULSInteractableComponent>(TEXT("Interactable"));
	Interactable->SetupAttachment(Mesh);
	Interactable->Prompt = NSLOCTEXT("LS", "PickUp", "Pick up");
	Interactable->Radius = 180.f;
}

FName ALSJournalPickup::CollectedFlag() const
{
	return FName(*FString::Printf(TEXT("collected_%s"), *JournalId.ToString()));
}

void ALSJournalPickup::ConfigureRules()
{
	const FString Flag = CollectedFlag().ToString();
	FLSInteractionRule Rule;
	Rule.If = { TEXT("!") + Flag };
	FLSStoryAction Set;
	Set.Type = ELSActionType::SetFlag;
	Set.Arg = Flag;
	FLSStoryAction Add;
	Add.Type = ELSActionType::AddJournal;
	Add.Arg = JournalId.ToString();
	Rule.Do = { Set, Add };
	Interactable->Rules = { Rule };
}

void ALSJournalPickup::BeginPlay()
{
	ConfigureRules();
	Super::BeginPlay();
	MeshBase = Mesh->GetRelativeLocation();
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnFlagChanged.AddDynamic(this, &ALSJournalPickup::HandleFlagChanged);
	}
	UpdateVisibility();
}

void ALSJournalPickup::HandleFlagChanged(FName Flag, bool)
{
	if (Flag == CollectedFlag()) UpdateVisibility();
}

void ALSJournalPickup::UpdateVisibility()
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	const bool bCollected = Story && Story->HasFlag(CollectedFlag());
	SetActorHiddenInGame(bCollected);
	SetActorTickEnabled(!bCollected);
}

void ALSJournalPickup::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	Time += DeltaTime;
	// Gentle bob and spin so pages read as pickups.
	Mesh->AddLocalRotation(FRotator(0.f, 40.f * DeltaTime, 0.f));
	Mesh->SetRelativeLocation(MeshBase + FVector(0.f, 0.f, FMath::Sin(Time * 2.f) * 6.f));
}

// ---------------------------------------------------------------- ALSStoryNPC

ALSStoryNPC::ALSStoryNPC()
{
	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	RootComponent = Capsule;
	Capsule->InitCapsuleSize(40.f, 90.f);
	Capsule->SetCollisionProfileName(TEXT("Pawn"));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Capsule);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetRelativeScale3D(FVector(0.7f, 0.7f, 1.8f));
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, -90.f));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cylinder.Succeeded()) Mesh->SetStaticMesh(Cylinder.Object);

	Interactable = CreateDefaultSubobject<ULSInteractableComponent>(TEXT("Interactable"));
	Interactable->SetupAttachment(Capsule);
	Interactable->Prompt = NSLOCTEXT("LS", "Talk", "Talk");
	Interactable->Radius = 250.f;
}

void ALSStoryNPC::BeginPlay()
{
	Super::BeginPlay();
	Interactable->OnInteracted.AddDynamic(this, &ALSStoryNPC::HandleInteracted);
}

void ALSStoryNPC::HandleInteracted(AActor* By)
{
	if (!By) return;
	FVector To = By->GetActorLocation() - GetActorLocation();
	To.Z = 0.f;
	if (!To.IsNearlyZero()) SetActorRotation(To.Rotation());
}

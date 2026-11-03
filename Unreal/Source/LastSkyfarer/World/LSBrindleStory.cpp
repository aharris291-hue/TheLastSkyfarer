// The Last Skyfarer: Brindle Isle story director.

#include "LSBrindleStory.h"

#include "Camera/CameraActor.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GliderComponent.h"
#include "LSPlayerCharacter.h"
#include "LSStorySubsystem.h"
#include "LSTimeOfDayDirector.h"
#include "PikoCompanion.h"
#include "WindVolume.h"

namespace
{
	const FName RevealedWindTag = TEXT("revealed_wind_1");
	const FName ImpossibleRouteTag = TEXT("impossible_route");
}

ALSBrindleStory::ALSBrindleStory()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetHidden(true);
}

void ALSBrindleStory::BeginPlay()
{
	Super::BeginPlay();
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnStoryEvent.AddUniqueDynamic(this, &ALSBrindleStory::HandleStoryEvent);
		Story->OnFlagChanged.AddUniqueDynamic(this, &ALSBrindleStory::HandleFlagChanged);
	}
}

void ALSBrindleStory::FindPiko()
{
	if (Piko)
	{
		return;
	}
	for (TActorIterator<APikoCompanion> It(GetWorld()); It; ++It)
	{
		Piko = *It;
		Piko->OnSensedCurrent.AddUniqueDynamic(this, &ALSBrindleStory::HandlePikoSensed);
		ApplyStoryState();
		break;
	}
}

void ALSBrindleStory::ApplyStoryState()
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!Story)
	{
		return;
	}
	const bool bCompass = Story->HasFlag(TEXT("compass_active"));
	const bool bPikoJoined = Story->HasFlag(TEXT("piko_joined"));

	if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		if (ALSPlayerCharacter* K = Cast<ALSPlayerCharacter>(PC->GetPawn()))
		{
			// The glider only deploys once Piko has joined and the glider is Kieran's (windrest.gd piko_joins).
			K->Glider->bHasGlider = Story->HasFlag(TEXT("has_glider"));
		}
	}
	if (GliderProp)
	{
		GliderProp->SetActorHiddenInGame(!(bCompass && !bPikoJoined));
		GliderProp->SetActorEnableCollision(bCompass && !bPikoJoined);
	}
	if (EdgeWall)
	{
		EdgeWall->SetActorEnableCollision(!bPikoJoined);
	}
	for (AActor* Prop : CompartmentProps)
	{
		if (Prop)
		{
			Prop->SetActorHiddenInGame(!Story->HasFlag(TEXT("compartment_open")));
		}
	}
	if (Piko)
	{
		// Piko appears at the story point where he meets Kieran: first sitting on the glider, then following.
		Piko->SetActorHiddenInGame(!(bCompass || bPikoJoined));
		Piko->SetActorTickEnabled(bPikoJoined);
		if (bCompass && !bPikoJoined)
		{
			Piko->SetActorLocation(PikoPerch);
		}
	}
	for (TActorIterator<AWindVolume> It(GetWorld()); It; ++It)
	{
		if ((It->ActorHasTag(ImpossibleRouteTag) && bCompass) || (It->ActorHasTag(RevealedWindTag) && Story->HasFlag(RevealedWindTag)))
		{
			It->Reveal();
		}
	}
	for (TActorIterator<ALSTimeOfDayDirector> It(GetWorld()); It; ++It)
	{
		It->ApplyTimeOfDay(Story->GetTimeOfDay(), true);
	}
}

void ALSBrindleStory::Queue(FName Conversation, float Delay)
{
	FStep S;
	S.Delay = Delay;
	S.Conversation = Conversation;
	Steps.Add(MoveTemp(S));
}

void ALSBrindleStory::QueueRun(TFunction<void()> Run, float Delay)
{
	FStep S;
	S.Delay = Delay;
	S.Run = MoveTemp(Run);
	Steps.Add(MoveTemp(S));
}

void ALSBrindleStory::FadeThrough(TFunction<void()> Middle, const FText& Caption)
{
	QueueRun([this, Caption]()
	{
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			PC->PlayerCameraManager->StartCameraFade(0.f, 1.f, 0.6f, FLinearColor::Black, false, true);
		}
		if (!Caption.IsEmpty())
		{
			Notify(Caption);
		}
	});
	QueueRun([this, Middle]()
	{
		Middle();
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			PC->PlayerCameraManager->StartCameraFade(1.f, 0.f, 0.9f, FLinearColor::Black, false, false);
		}
	}, 0.8f);
}

void ALSBrindleStory::Notify(const FText& Message)
{
	if (ULSStorySubsystem* Story = ULSStorySubsystem::Get(this))
	{
		Story->OnNotify.Broadcast(Message);
	}
}

void ALSBrindleStory::Teleport(const FTransform& Where)
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	ACharacter* K = PC ? Cast<ACharacter>(PC->GetPawn()) : nullptr;
	if (!K)
	{
		return;
	}
	K->SetActorLocationAndRotation(Where.GetLocation(), Where.Rotator(), false, nullptr, ETeleportType::TeleportPhysics);
	PC->SetControlRotation(Where.Rotator());
}

void ALSBrindleStory::HandleStoryEvent(FName EventId)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	UE_LOG(LogTemp, Display, TEXT("LS_STORY event %s"), *EventId.ToString());

	if (EventId == TEXT("sunset_fade"))
	{
		FadeThrough([Story]() { Story->SetTimeOfDay(TEXT("Sunset")); }, NSLOCTEXT("LS", "LaterThatDay", "Later that day..."));
		Queue(TEXT("maren_deed"), 0.6f);
	}
	else if (EventId == TEXT("enter_workshop"))
	{
		FadeThrough([this, Story]()
		{
			Teleport(InteriorSpawn);
			// Indoors at night: lamplight inside, moonlight outside (workshop.gd after_ready).
			Story->SetTimeOfDay(TEXT("Night"));
		});
		if (!Story->HasFlag(TEXT("workshop_entered")))
		{
			QueueRun([this, Story]()
			{
				Story->SetFlag(TEXT("workshop_entered"));
				Story->DiscoverLocation(TEXT("workshop"));
				Notify(NSLOCTEXT("LS", "Chapter2", "Chapter 2: The Hidden Workshop"));
			});
			Queue(TEXT("workshop_enter"), 1.2f);
		}
	}
	else if (EventId == TEXT("compass_awakens"))
	{
		Queue(TEXT("compass_awakens"), 0.4f);
	}
	else if (EventId == TEXT("next_morning"))
	{
		// StoryEvents.json has already moved the story to Chapter 3 at dawn and started Into the Clouds.
		QueueRun([this]() { Notify(NSLOCTEXT("LS", "Chapter2Done", "Chapter 2 complete. An impossible wind current appears on the map.")); });
		FadeThrough([this, Story]()
		{
			Teleport(DoorSpawn);
			ApplyStoryState();
			Story->SetFlag(TEXT("chapter3_banner"));
		}, FText::GetEmpty());
		QueueRun([this, Story]()
		{
			Notify(NSLOCTEXT("LS", "Chapter3", "Chapter 3: Into the Clouds"));
			Story->SaveToSlot(TEXT("autosave"));
		}, 0.5f);
	}
	else if (EventId == TEXT("leave"))
	{
		FadeThrough([this]() { Teleport(DoorSpawn); });
	}
	else if (EventId == TEXT("piko_joins"))
	{
		Story->SetFlag(TEXT("has_glider"));
		ApplyStoryState();
		QueueRun([this, Story]()
		{
			Notify(NSLOCTEXT("LS", "GlideTutorial", "Jump off the edge, then press Jump again to glide. Rising wind lifts you higher."));
			Story->SaveToSlot(TEXT("autosave"));
		});
	}
	else if (EventId == TEXT("demo_end"))
	{
		QueueRun([this, Story]()
		{
			Story->SaveToSlot(TEXT("autosave"));
			bDemoEnded = true;
			EndCamera = GetWorld()->SpawnActor<ACameraActor>(EndView.GetLocation(), EndView.Rotator());
			if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
			{
				PC->SetViewTargetWithBlend(EndCamera, 2.5f, VTBlend_EaseInOut, 2.f);
			}
			Notify(NSLOCTEXT("LS", "DemoEnd", "End of the Windrest demo. Thank you for playing."));
		}, 0.6f);
	}
}

void ALSBrindleStory::HandleFlagChanged(FName Flag, bool bSet)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (!bSet || !Story)
	{
		return;
	}
	if (Flag == TEXT("compartment_open") || Flag == TEXT("compass_active") || Flag == TEXT("piko_joined"))
	{
		ApplyStoryState();
	}
	// workshop.gd: once the three searches are done, Kieran says so (once).
	if ((Flag == TEXT("searched_maps") || Flag == TEXT("searched_sketches") || Flag == TEXT("searched_notes"))
		&& Story->IsObjectiveDone(TEXT("hidden_workshop"), TEXT("search")) && !Story->HasFlag(TEXT("search_done_said")))
	{
		Story->SetFlag(TEXT("search_done_said"));
		Queue(TEXT("search_done"), 0.3f);
	}
}

void ALSBrindleStory::HandlePikoSensed(int32 NumRevealed)
{
	ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (NumRevealed <= 0 || !Story)
	{
		return;
	}
	Story->SetFlag(RevealedWindTag);
	if (!Story->HasFlag(TEXT("seen_piko_wind")))
	{
		Story->SetFlag(TEXT("seen_piko_wind"));
		Queue(TEXT("piko_found_wind"), 0.4f);
	}
}

void ALSBrindleStory::UpdateFog()
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	const APawn* K = PC ? PC->GetPawn() : nullptr;
	AExponentialHeightFog* Fog = nullptr;
	for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It)
	{
		Fog = *It;
		break;
	}
	if (!K || !Fog)
	{
		return;
	}
	const float Target = bDemoEnded ? 1.f : FMath::Clamp((K->GetActorLocation().Y - FogStartY) / (FogFullY - FogStartY), 0.f, 1.f);
	if (Target <= 0.f && FogAmount <= 0.f)
	{
		BaseFogDensity = -1.f; // the time-of-day director owns the fog here
		return;
	}
	UExponentialHeightFogComponent* F = Fog->GetComponent();
	if (BaseFogDensity < 0.f)
	{
		BaseFogDensity = F->FogDensity;
		BaseFogColor = F->FogInscatteringLuminance;
	}
	FogAmount = Target;
	F->SetFogDensity(FMath::Lerp(BaseFogDensity, FogDensity, FogAmount));
	F->SetFogInscatteringColor(FMath::Lerp(BaseFogColor, FogColor, FogAmount));
}

void ALSBrindleStory::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	FindPiko();
	UpdateFog();

	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	if (Steps.Num() == 0 || !Story || Story->IsInDialogue())
	{
		return;
	}
	FStep& S = Steps[0];
	S.Delay -= DeltaSeconds;
	if (S.Delay > 0.f)
	{
		return;
	}
	FStep Done = MoveTemp(S);
	Steps.RemoveAt(0);
	if (!Done.Conversation.IsNone())
	{
		ULSStorySubsystem::Get(this)->StartConversation(Done.Conversation);
	}
	if (Done.Run)
	{
		Done.Run();
	}
}

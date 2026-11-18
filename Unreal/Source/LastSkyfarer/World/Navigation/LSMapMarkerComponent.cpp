#include "LSMapMarkerComponent.h"

#include "LSRestorationTypes.h"
#include "LSStorySubsystem.h"
#include "Engine/World.h"

void ULSMapMarkerComponent::BeginPlay()
{
	Super::BeginPlay();
	if (ULSMapSubsystem* Map = GetWorld()->GetSubsystem<ULSMapSubsystem>()) Map->Register(this);
}

void ULSMapMarkerComponent::EndPlay(const EEndPlayReason::Type Reason)
{
	if (UWorld* World = GetWorld())
	{
		if (ULSMapSubsystem* Map = World->GetSubsystem<ULSMapSubsystem>()) Map->Unregister(this);
	}
	Super::EndPlay(Reason);
}

bool ULSMapMarkerComponent::Evaluate(const ULSStorySubsystem& Story, FLSMapMarkerView& Out) const
{
	if (!Story.CheckAll(VisibleIf)) return false;

	Out = FLSMapMarkerView();
	Out.Kind = Kind;
	Out.WorldLocation = GetComponentLocation();
	Out.Label = Label;

	switch (Kind)
	{
	case ELSMapMarkerKind::Landmark:
	{
		Out.Knowledge = Story.GetMapKnowledge(LocationId);
		if (Out.Knowledge == ELSMapKnowledge::Unknown) return false;
		if (Out.Label.IsEmpty())
		{
			if (const FLSLocationDef* Loc = Story.GetDatabase().Locations.Find(LocationId)) Out.Label = Loc->Name;
		}
		return true;
	}
	case ELSMapMarkerKind::Objective:
	{
		if (Story.GetQuestState(QuestId) != ELSQuestState::Active || Story.IsObjectiveDone(QuestId, ObjectiveId)) return false;
		const FLSObjectiveDef* Obj = Story.GetDatabase().FindObjective(QuestId, ObjectiveId);
		if (!Obj || !Story.CheckAll(Obj->HiddenUntil)) return false;
		if (Out.Label.IsEmpty()) Out.Label = Obj->Text;
		Out.bTracked = Story.GetTrackedQuest() == QuestId;
		return true;
	}
	case ELSMapMarkerKind::FastTravel:
		return Story.HasFlag(ULSRestorationLibrary::StageFlag(BeaconId, ELSRestorationStage::Advanced));
	}
	return false;
}

TArray<FLSMapMarkerView> ULSMapSubsystem::GetVisibleMarkers(const ULSStorySubsystem& Story) const
{
	TArray<FLSMapMarkerView> Out;
	for (const TWeakObjectPtr<ULSMapMarkerComponent>& Weak : Markers)
	{
		FLSMapMarkerView View;
		if (const ULSMapMarkerComponent* M = Weak.Get(); M && M->Evaluate(Story, View)) Out.Add(View);
	}
	return Out;
}

TArray<FLSMapMarkerView> ULSMapSubsystem::K2_GetVisibleMarkers() const
{
	const ULSStorySubsystem* Story = ULSStorySubsystem::Get(this);
	return Story ? GetVisibleMarkers(*Story) : TArray<FLSMapMarkerView>();
}

bool ULSMapSubsystem::FindCompassTarget(const ULSStorySubsystem& Story, const FVector& From, FVector& OutTarget) const
{
	float BestTracked = TNumericLimits<float>::Max();
	float BestOther = TNumericLimits<float>::Max();
	FVector Tracked, Other;
	for (const FLSMapMarkerView& V : GetVisibleMarkers(Story))
	{
		if (V.Kind != ELSMapMarkerKind::Objective) continue;
		const float D = FVector::DistSquared(From, V.WorldLocation);
		if (V.bTracked && D < BestTracked) { BestTracked = D; Tracked = V.WorldLocation; }
		if (!V.bTracked && D < BestOther) { BestOther = D; Other = V.WorldLocation; }
	}
	if (BestTracked < TNumericLimits<float>::Max()) { OutTarget = Tracked; return true; }
	if (BestOther < TNumericLimits<float>::Max()) { OutTarget = Other; return true; }
	if (Story.GetMapPins().Num() > 0) { OutTarget = Story.GetMapPins().Last(); return true; }
	return false;
}

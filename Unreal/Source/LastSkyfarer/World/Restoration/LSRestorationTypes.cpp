#include "LSRestorationTypes.h"

#include "LSStorySubsystem.h"

void FLSRingPuzzle::Reset(const TArray<FLSRingDef>& InRings)
{
	Rings = InRings;
	Positions.Reset();
	for (const FLSRingDef& R : Rings)
	{
		const int32 N = FMath::Max(R.NumGlyphs, 2);
		Positions.Add(((R.Start % N) + N) % N);
	}
}

bool FLSRingPuzzle::Rotate(int32 Ring, int32 Steps)
{
	if (!Positions.IsValidIndex(Ring)) return false;
	const int32 N = FMath::Max(Rings[Ring].NumGlyphs, 2);
	Positions[Ring] = (((Positions[Ring] + Steps) % N) + N) % N;
	return true;
}

bool FLSRingPuzzle::IsRingAligned(int32 Ring) const
{
	if (!Positions.IsValidIndex(Ring)) return false;
	const int32 N = FMath::Max(Rings[Ring].NumGlyphs, 2);
	return Positions[Ring] == ((Rings[Ring].Target % N) + N) % N;
}

bool FLSRingPuzzle::IsSolved() const
{
	for (int32 i = 0; i < Positions.Num(); ++i)
	{
		if (!IsRingAligned(i)) return false;
	}
	return Positions.Num() > 0;
}

FName ULSRestorationLibrary::StageFlag(FName Id, ELSRestorationStage Stage)
{
	static const TCHAR* Names[] = { TEXT(""), TEXT("discovered"), TEXT("investigated"), TEXT("restored"),
		TEXT("synchronized"), TEXT("reacted"), TEXT("advanced") };
	const int32 i = static_cast<int32>(Stage);
	if (i <= 0 || i >= UE_ARRAY_COUNT(Names) || Id.IsNone()) return NAME_None;
	return FName(*FString::Printf(TEXT("beacon_%s_%s"), *Id.ToString(), Names[i]));
}

ELSRestorationStage ULSRestorationLibrary::GetStage(const ULSStorySubsystem& Story, FName Id)
{
	for (int32 i = static_cast<int32>(ELSRestorationStage::Advanced); i > 0; --i)
	{
		if (Story.HasFlag(StageFlag(Id, static_cast<ELSRestorationStage>(i))))
		{
			return static_cast<ELSRestorationStage>(i);
		}
	}
	return ELSRestorationStage::Unknown;
}

bool ULSRestorationLibrary::AdvanceTo(ULSStorySubsystem& Story, FName Id, ELSRestorationStage Stage,
	const TMap<ELSRestorationStage, FLSStoryActionList>* StageActions)
{
	const int32 From = static_cast<int32>(GetStage(Story, Id));
	const int32 To = static_cast<int32>(Stage);
	if (To <= From || Id.IsNone()) return false;

	for (int32 i = From + 1; i <= To; ++i)
	{
		const ELSRestorationStage S = static_cast<ELSRestorationStage>(i);
		Story.SetFlag(StageFlag(Id, S));
		if (StageActions)
		{
			if (const FLSStoryActionList* List = StageActions->Find(S)) Story.RunActions(List->Actions);
		}
	}
	return true;
}

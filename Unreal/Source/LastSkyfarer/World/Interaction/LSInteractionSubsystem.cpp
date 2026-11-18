#include "LSInteractionSubsystem.h"

#include "LSInteractableComponent.h"

ULSInteractableComponent* ULSInteractionSubsystem::FindBest(const FVector& Location, const FVector& Forward, const ULSStorySubsystem& Story) const
{
	ULSInteractableComponent* Best = nullptr;
	float BestScore = TNumericLimits<float>::Max();
	const FVector Facing = Forward.GetSafeNormal2D();

	for (const TWeakObjectPtr<ULSInteractableComponent>& Weak : Interactables)
	{
		ULSInteractableComponent* I = Weak.Get();
		if (!I || !I->CanInteractWith(Story)) continue;

		const FVector To = I->GetComponentLocation() - Location;
		const float Dist = To.Size();
		if (Dist > I->Radius) continue;

		// Things in front win over things behind at the same distance.
		const float Dot = Facing.IsNearlyZero() ? 1.f : FVector::DotProduct(Facing, To.GetSafeNormal2D());
		const float Score = Dist + (1.f - Dot) * 100.f;
		if (Score < BestScore)
		{
			BestScore = Score;
			Best = I;
		}
	}
	return Best;
}

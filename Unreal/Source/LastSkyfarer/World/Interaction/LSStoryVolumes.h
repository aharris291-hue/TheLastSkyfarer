// The Last Skyfarer: level actors that drive the story (ports of the Godot TriggerZone,
// location areas, collectibles and NPCs).

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSNarrativeTypes.h"
#include "LSStoryVolumes.generated.h"

class UBoxComponent;
class UCapsuleComponent;
class UStaticMeshComponent;
class ULSInteractableComponent;

/** Fires once when the player walks in and the conditions pass: plays a conversation and/or runs actions. */
UCLASS(Blueprintable)
class LASTSKYFARER_API ALSStoryTrigger : public AActor
{
	GENERATED_BODY()

public:
	ALSStoryTrigger();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<UBoxComponent> Box;

	/** Set when the trigger fires; the trigger never fires again while it is set. Required. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FName OnceFlag;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TArray<FString> Conditions;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FName Conversation;

	/** Run when the trigger fires, before the conversation. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	TArray<FLSStoryAction> Actions;

	/** True if it fired. Exposed for tests and Blueprints. */
	UFUNCTION(BlueprintCallable, Category = "Story")
	bool TryFire(AActor* Other);

protected:
	virtual void BeginPlay() override;

private:
	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Hit);
};

/** Marks a named area. Entering it discovers the location (Locations.json) and shows its name. */
UCLASS(Blueprintable)
class LASTSKYFARER_API ALSLocationVolume : public AActor
{
	GENERATED_BODY()

public:
	ALSLocationVolume();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<UBoxComponent> Box;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FName LocationId;

protected:
	virtual void BeginPlay() override;

private:
	UFUNCTION()
	void HandleOverlap(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Hit);
};

/** A journal page (or other journal discovery). Picking it up sets collected_<id> and adds the entry. */
UCLASS(Blueprintable)
class LASTSKYFARER_API ALSJournalPickup : public AActor
{
	GENERATED_BODY()

public:
	ALSJournalPickup();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<ULSInteractableComponent> Interactable;

	/** Journal entry id (Journal.json). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FName JournalId;

	UFUNCTION(BlueprintPure, Category = "Story")
	FName CollectedFlag() const;

	/** Builds the pickup rule from JournalId (called at BeginPlay; public for tests). */
	void ConfigureRules();

	virtual void Tick(float DeltaTime) override;

protected:
	virtual void BeginPlay() override;

private:
	UFUNCTION()
	void HandleFlagChanged(FName Flag, bool bSet);

	void UpdateVisibility();
	float Time = 0.f;
	FVector MeshBase = FVector::ZeroVector;
};

/** A villager: placeholder capsule and mesh plus a Talk interactable. Turns to face Kieran when spoken to. */
UCLASS(Blueprintable)
class LASTSKYFARER_API ALSStoryNPC : public AActor
{
	GENERATED_BODY()

public:
	ALSStoryNPC();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<UCapsuleComponent> Capsule;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<UStaticMeshComponent> Mesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Story")
	TObjectPtr<ULSInteractableComponent> Interactable;

	/** Speaker id (Speakers.json), for name tags and the dialogue camera. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story")
	FName SpeakerId;

protected:
	virtual void BeginPlay() override;

private:
	UFUNCTION()
	void HandleInteracted(AActor* By);
};

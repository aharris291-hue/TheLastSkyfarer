// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class LastSkyfarer : ModuleRules
{
	public LastSkyfarer(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate",
			"Json",
			"JsonUtilities"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { "SlateCore" });

		PublicIncludePaths.AddRange(new string[] {
			"LastSkyfarer",
			"LastSkyfarer/Narrative",
			"LastSkyfarer/Player",
			"LastSkyfarer/World",
			"LastSkyfarer/World/Interaction",
			"LastSkyfarer/World/Restoration",
			"LastSkyfarer/World/Navigation",
			"LastSkyfarer/Companion",
			"LastSkyfarer/UI",
			"LastSkyfarer/Variant_Platforming",
			"LastSkyfarer/Variant_Platforming/Animation",
			"LastSkyfarer/Variant_Combat",
			"LastSkyfarer/Variant_Combat/AI",
			"LastSkyfarer/Variant_Combat/Animation",
			"LastSkyfarer/Variant_Combat/Gameplay",
			"LastSkyfarer/Variant_Combat/Interfaces",
			"LastSkyfarer/Variant_Combat/UI",
			"LastSkyfarer/Variant_SideScrolling",
			"LastSkyfarer/Variant_SideScrolling/AI",
			"LastSkyfarer/Variant_SideScrolling/Gameplay",
			"LastSkyfarer/Variant_SideScrolling/Interfaces",
			"LastSkyfarer/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}

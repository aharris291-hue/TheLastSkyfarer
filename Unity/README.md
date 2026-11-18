# The Last Skyfarer (Unity)

Adam switched the project from Unreal to Unity on 2026-11-17 and asked for the game to be rebuilt from the ground up.
The Unreal project (`Unreal/`) and the Godot files stay in the repo as read-only reference.

- Engine: Unity 6 (6000.6.9f1), Universal Render Pipeline, created from the bundled URP Blank template (no downloads).
- Project: `Unity/LastSkyfarer`. Open it with Unity 6000.6.9f1.
- Quality: "Low" is the default level (render scale 0.7, MSAA off, one shadow cascade, no HDR) for Intel UHD 630 class
  graphics; the game itself will cap the frame rate at 30 on Low. "Mobile" and "PC" from the template remain as higher tiers.
- Settings: Force Text serialization, Visible Meta Files. Generated folders (Library, Temp, Logs, obj, Builds,
  UserSettings) are git-ignored; large art and audio go through Git LFS (`Unity/.gitattributes`).
- One-off setup: `Assets/Editor/ProjectSetup.cs`, run with
  `Unity.exe -batchmode -projectPath Unity/LastSkyfarer -executeMethod LastSkyfarer.EditorTools.ProjectSetup.Run -quit`.

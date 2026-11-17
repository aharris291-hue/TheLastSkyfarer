# Asset Manifest (Unity)

Every asset in `Unity/LastSkyfarer/Assets` that is not plain code or data: where it came from, its licence, and how it
was changed. Add a row whenever an asset is added or replaced. Unreal-only content (Epic's mannequin and its
animations, template and starter content) is never copied into Unity.

| Asset | Source | Licence | Notes |
|---|---|---|---|
| `Art/Characters/Kieran/Model/Kieran_Thorn_GameReady.fbx`, `T_Kieran_BaseColor.png` | Built in Blender by `Unreal/Tools/blender/kieran/*.py` from Adam's turnaround | Project-owned (original) | Body base from MPFB/MakeHuman with CC0 assets (body, eyes, eyebrows, eyelashes, teeth); clothes, hair, accessories and the painted atlas are ours. 45k triangles, 53-bone skeleton, set up as a Unity Humanoid avatar |
| `Art/Characters/Kieran/Animations/Kieran_Glide.fbx` | Posed in Blender by `glide_pose.py`, after Adam's reference (horizontal, hands on the bar) | Project-owned (original) | Retargeted through Humanoid |
| `Art/Characters/Kieran/Animations/Mixamo_*.fbx` (Idle, Walking, Running, Jumping Up, Falling Idle, Falling To Landing, Climbing Up Wall) | Adobe Mixamo (mixamo.com), downloaded by Adam on 2026-11-17 as FBX for Unity, without skin, in place, 30 fps | Mixamo terms: free, royalty-free use in commercial and non-commercial games and projects; the animations may not be redistributed on their own as standalone files | Retargeted onto Kieran through Humanoid. Adam's originals stay in `D:\TheLastSkyfarer\Mixamo` |
| `Settings/*` (URP assets, Low level) | Unity URP Blank template, tuned by `Editor/ProjectSetup.cs` | Unity Companion Licence (part of the engine) | |

# The Last Skyfarer

A storybook fantasy adventure about Kieran Thorn, a young courier who becomes the first Skyfarer in generations.

## Main build: Unreal Engine 5.8 (3D)

- Project: [Unreal/LastSkyfarer.uproject](Unreal/LastSkyfarer.uproject), a C++ project made from the Third Person template.
- Production brief: [docs/UNREAL_PRODUCTION_PROMPT.md](docs/UNREAL_PRODUCTION_PROMPT.md).
- Current status: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).
- Large binary files (uasset, umap, fbx, wav, png, tga, exr, psd, blend) are stored with Git LFS. Run `git lfs install` before cloning.

## Archived: Godot 4.3 demo (2D, reference only)

The original Windrest Village demo (version 0.1.0-demo) stays in the repo untouched as a reference for dialogue, quests, layout and lessons learned. Its files are `project.godot`, `scenes/`, `scripts/`, `data/`, `assets/`, `art_source/`, `tests/`, `builds/`, `tools/` and `export_presets.cfg`.

- Open the root folder in Godot 4.3 and press Play.
- Tests: `godot --headless --path . res://tests/test_runner.tscn`

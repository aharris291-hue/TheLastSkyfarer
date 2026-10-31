# Performance Report

**Status: not yet profiled on real Windows hardware.** The only numbers available come from this build environment, which has no GPU.

| Measure | Value | Notes |
|---|---|---|
| Windrest at 1920x1080, software renderer (llvmpipe, 4 CPU cores) | 15 to 17 FPS | CPU-only rasterising; not representative of any real PC |
| Windows export size | 95 MB | Single exe with embedded pack; most of it is art at 4x |
| Scripts | about 4,300 lines GDScript | |

## Expectations

The scene is 2D sprites with a sky shader and parallax layers, which any integrated GPU from the last ten years should hold at 60 FPS. That is an expectation, not a measurement.

## To do before release

- Run on a low-end Windows laptop (integrated graphics) and a typical desktop; record FPS, frame time and memory with Godot's profiler.
- Compress large textures (VRAM compression) and reduce the 4x environment props if memory is high.

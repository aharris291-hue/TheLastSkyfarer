// The Last Skyfarer: builds Brindle Isle's ground for the polish pass. A 3 m height-and-paint grid over the island's
// ellipse: gentle rolling meadows, flattened (with soft shoulders) wherever a building, path, prop or story place
// stands, fading to level at the rim. Painted grass, worn dirt along paths and round buildings, cobbles in the village
// and wildflower meadows. Meshed in chunks with colliders; trees, rocks, fences and other dressing are set down on it.
using System.Collections.Generic;
using System.IO;
using LastSkyfarer.World;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace LastSkyfarer.EditorTools
{
    public static class IslandTerrainBuilder
    {
        const float RadiusX = 700f, RadiusZ = 575f, Spacing = 3f;
        const int Chunk = 48;
        const string MeshDir = "Assets/Art/Generated/Terrain";

        public struct Zone
        {
            public Vector2 Centre, Half; public float Yaw, Margin; public bool Round;
            public float Distance(float x, float z)
            {
                if (Round) return new Vector2(x - Centre.x, z - Centre.y).magnitude - Half.x;
                float c = Mathf.Cos(-Yaw * Mathf.Deg2Rad), s = Mathf.Sin(-Yaw * Mathf.Deg2Rad);
                float dx = x - Centre.x, dz = z - Centre.y;
                float lx = Mathf.Abs(dx * c - dz * s) - Half.x, lz = Mathf.Abs(dx * s + dz * c) - Half.y;
                return new Vector2(Mathf.Max(lx, 0f), Mathf.Max(lz, 0f)).magnitude + Mathf.Min(Mathf.Max(lx, lz), 0f);
            }
            public static Zone FromBounds(Bounds b, float margin) => new Zone { Centre = new Vector2(b.center.x, b.center.z), Half = new Vector2(b.extents.x, b.extents.z), Margin = margin };
            public static Zone FromTransform(Transform t, Vector2 size, float margin) => new Zone { Centre = new Vector2(t.position.x, t.position.z), Half = size * 0.5f, Yaw = t.eulerAngles.y, Margin = margin };
        }

        public class Input
        {
            public List<Zone> Flat = new List<Zone>();
            public List<Zone> Dirt = new List<Zone>();
            public List<Zone> Cobble = new List<Zone>();
            public List<Transform> Snap = new List<Transform>();
        }

        static float Fbm(float x, float z)
        {
            float h = (Mathf.PerlinNoise(x / 140f + 13.1f, z / 140f + 7.7f) - 0.45f) * 3.2f;
            h += (Mathf.PerlinNoise(x / 45f + 3.3f, z / 45f + 1.9f) - 0.5f) * 1.2f;
            h += (Mathf.PerlinNoise(x / 15f + 9.2f, z / 15f + 4.4f) - 0.5f) * 0.25f;
            return Mathf.Max(0f, h + 0.6f);
        }

        public static IslandGround Build(Transform parent, Input input, Material ground, Mesh grassMesh, Mesh flowerMesh, Material grass, Material flower)
        {
            int w = Mathf.CeilToInt(RadiusX * 2f / Spacing) + 3, h = Mathf.CeilToInt(RadiusZ * 2f / Spacing) + 3;
            var origin = new Vector2(-RadiusX - Spacing, -RadiusZ - Spacing);
            var heights = new float[w * h];
            var paint = new Color32[w * h];
            for (int iz = 0; iz < h; iz++)
                for (int ix = 0; ix < w; ix++)
                {
                    float x = origin.x + ix * Spacing, z = origin.y + iz * Spacing;
                    float r = Mathf.Sqrt((x / RadiusX) * (x / RadiusX) + (z / RadiusZ) * (z / RadiusZ));
                    float flat = Mathf.Clamp01((0.97f - r) / 0.06f);                      // level at the rim
                    float dirt = 0f, cobble = 0f;
                    foreach (var f in input.Flat)
                    {
                        float d = f.Distance(x, z);
                        if (d < f.Margin) flat = Mathf.Min(flat, Mathf.SmoothStep(0f, 1f, d / f.Margin));
                    }
                    foreach (var f in input.Dirt) dirt = Mathf.Max(dirt, 1f - Mathf.Clamp01(f.Distance(x, z) / f.Margin));
                    foreach (var f in input.Cobble) cobble = Mathf.Max(cobble, 1f - Mathf.Clamp01(f.Distance(x, z) / f.Margin));
                    heights[iz * w + ix] = Fbm(x, z) * flat;
                    float meadow = Mathf.Clamp01((Mathf.PerlinNoise(x / 60f + 31f, z / 60f + 17f) - 0.55f) * 4f) * Mathf.Clamp01((new Vector2(x, z).magnitude - 70f) / 40f);
                    paint[iz * w + ix] = new Color(1f, dirt, cobble, meadow);
                }

            var root = new GameObject("IslandGround").transform;
            root.SetParent(parent, false);
            var ig = root.gameObject.AddComponent<IslandGround>();
            ig.Origin = origin; ig.Spacing = Spacing; ig.Width = w; ig.Height = h; ig.Heights = heights; ig.Paint = paint;
            ig.GrassMesh = grassMesh; ig.FlowerMesh = flowerMesh; ig.GrassMaterial = grass; ig.FlowerMaterial = flower;

            Directory.CreateDirectory(MeshDir);
            int chunks = 0;
            for (int cz = 0; cz < h - 1; cz += Chunk)
                for (int cx = 0; cx < w - 1; cx += Chunk)
                {
                    var mesh = ChunkMesh(ig, cx, cz, Mathf.Min(Chunk, w - 1 - cx), Mathf.Min(Chunk, h - 1 - cz));
                    if (mesh == null) continue;
                    string path = $"{MeshDir}/Ground_{cx}_{cz}.asset";
                    AssetDatabase.DeleteAsset(path);
                    AssetDatabase.CreateAsset(mesh, path);
                    var go = new GameObject(mesh.name);
                    go.transform.SetParent(root, false);
                    go.AddComponent<MeshFilter>().sharedMesh = mesh;
                    var mr = go.AddComponent<MeshRenderer>();
                    mr.sharedMaterial = ground;
                    mr.shadowCastingMode = ShadowCastingMode.On;
                    go.AddComponent<MeshCollider>().sharedMesh = mesh;
                    GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
                    chunks++;
                }
            // Dressing stands on the slopes.
            foreach (var t in input.Snap) t.position += Vector3.up * ig.HeightAt(t.position.x, t.position.z);
            float max = 0f; foreach (float v in heights) max = Mathf.Max(max, v);
            Debug.Log($"LS_TERRAIN {w}x{h} grid, {chunks} chunks, highest {max:F1} m, {input.Flat.Count} flat zones, {input.Snap.Count} pieces set on the ground");
            return ig;
        }

        static Mesh ChunkMesh(IslandGround g, int cx, int cz, int nx, int nz)
        {
            var verts = new List<Vector3>(); var norms = new List<Vector3>(); var cols = new List<Color32>(); var tris = new List<int>();
            int stride = nx + 1;
            for (int z = 0; z <= nz; z++)
                for (int x = 0; x <= nx; x++)
                {
                    int ix = cx + x, iz = cz + z, i = iz * g.Width + ix;
                    float wx = g.Origin.x + ix * g.Spacing, wz = g.Origin.y + iz * g.Spacing;
                    verts.Add(new Vector3(wx, g.Heights[i], wz));
                    float hl = g.Heights[iz * g.Width + Mathf.Max(ix - 1, 0)], hr = g.Heights[iz * g.Width + Mathf.Min(ix + 1, g.Width - 1)];
                    float hd = g.Heights[Mathf.Max(iz - 1, 0) * g.Width + ix], hu = g.Heights[Mathf.Min(iz + 1, g.Height - 1) * g.Width + ix];
                    norms.Add(new Vector3(hl - hr, 2f * g.Spacing, hd - hu).normalized);
                    cols.Add(g.Paint[i]);
                }
            bool In(int ix, int iz)
            {
                float wx = g.Origin.x + ix * g.Spacing, wz = g.Origin.y + iz * g.Spacing;
                return (wx / RadiusX) * (wx / RadiusX) + (wz / RadiusZ) * (wz / RadiusZ) <= 1.0f;
            }
            for (int z = 0; z < nz; z++)
                for (int x = 0; x < nx; x++)
                {
                    int ix = cx + x, iz = cz + z;
                    if (!In(ix, iz) && !In(ix + 1, iz) && !In(ix, iz + 1) && !In(ix + 1, iz + 1)) continue;
                    if (!(In(ix, iz) && In(ix + 1, iz) && In(ix, iz + 1) && In(ix + 1, iz + 1))) continue;   // keep inside the rim
                    int a = z * stride + x;
                    tris.AddRange(new[] { a, a + stride, a + 1, a + 1, a + stride, a + stride + 1 });
                }
            if (tris.Count == 0) return null;
            var m = new Mesh { name = $"Ground_{cx}_{cz}", indexFormat = verts.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            m.SetVertices(verts); m.SetNormals(norms); m.SetColors(cols); m.SetTriangles(tris, 0);
            m.RecalculateBounds();
            return m;
        }

        // ------------------------------------------------------------ the island's rocky underside (polish pass 1)
        /// <summary>Layered cliffs from the rim down to a craggy point 210 m below: a near-vertical band of rock
        /// strata under the meadow, then tapering ledges. Each 7 m layer juts in or out a little, with darker
        /// corner shading under every lip (vertex colour R) and lit edges (G) for the painterly shader.</summary>
        public static GameObject BuildUnderside(Transform parent, Material rock)
        {
            const int seg = 192;
            var ys = new List<float> { 0f, -0.8f, -2.5f };
            for (float y = -5f; y > -205f; y -= 5.5f) ys.Add(y);
            ys.Add(-210f);
            var rnd = new System.Random(7);
            var layerOffset = new float[64];
            for (int i = 0; i < layerOffset.Length; i++) layerOffset[i] = (float)rnd.NextDouble() * 0.035f - 0.0175f;
            var v = new List<Vector3>(); var c = new List<Color>(); var t = new List<int>();
            for (int j = 0; j < ys.Count; j++)
            {
                float y = ys[j], depth = -y;
                float r = depth < 28f ? 1.0f - 0.0008f * depth : 0.976f * Mathf.Pow(Mathf.Max(0f, 1f - (depth - 28f) / 182f), 0.72f);
                r = Mathf.Max(r, 0.015f);
                int layer = Mathf.FloorToInt(depth / 7f);
                float lip = layerOffset[layer % layerOffset.Length];
                float underLip = depth % 7f < 2f && depth > 3f ? 1f : 0f;          // just below a ledge: in shadow
                for (int i = 0; i <= seg; i++)
                {
                    float a = i * Mathf.PI * 2f / seg;
                    float ca = Mathf.Cos(a), sa = Mathf.Sin(a);
                    float n = (Mathf.PerlinNoise(ca * 2.2f + 5f + layer * 0.37f, sa * 2.2f + 3f) - 0.5f) * 0.07f
                            + (Mathf.PerlinNoise(ca * 7f + 11f, sa * 7f + depth * 0.05f) - 0.5f) * 0.03f;
                    float k = r * (1f + (depth > 1f ? lip + n : 0f));
                    float yy = y + (depth > 3f ? (Mathf.PerlinNoise(ca * 5f, sa * 5f + depth) - 0.5f) * 2.5f : 0f);
                    v.Add(new Vector3(ca * RadiusX * k, yy, sa * RadiusZ * k));
                    c.Add(new Color(depth < 1f ? 1f : Mathf.Lerp(0.95f, 0.55f, underLip) * Mathf.Lerp(1f, 0.75f, Mathf.Clamp01(depth / 200f)), underLip > 0f ? 0f : 0.6f, 0f, 1f));
                }
            }
            for (int j = 0; j < ys.Count - 1; j++)
                for (int i = 0; i < seg; i++)
                {
                    int a = j * (seg + 1) + i, b2 = a + seg + 1;
                    t.AddRange(new[] { a, a + 1, b2, a + 1, b2 + 1, b2 });
                }
            var m = new Mesh { name = "IslandUnderside", indexFormat = IndexFormat.UInt32 };
            m.SetVertices(v); m.SetColors(c); m.SetTriangles(t, 0);
            m.RecalculateNormals(); m.RecalculateBounds();
            Directory.CreateDirectory(MeshDir);
            string path = $"{MeshDir}/IslandUnderside.asset";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path);
            var go = new GameObject("IslandUnderside");
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = rock;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            Debug.Log($"LS_TERRAIN underside {v.Count} vertices, {ys.Count} rings");
            return go;
        }

        /// <summary>A rocky plateau in place of the smooth art-pass-1 slab: a near-rectangular (superellipse) block
        /// with layered rock strata on its sides, flaring slightly at the foot, and a grassy cap on top. The cap
        /// stays inside the greybox collision box, so where Kieran can walk matches what he sees.</summary>
        public static GameObject BuildPlateau(Transform parent, string name, Vector3 centre, Vector3 size, Material rock, Material grass, int seed)
        {
            const int seg = 96;
            float hx = size.x * 0.5f, hz = size.z * 0.5f, h = size.y;
            var rnd = new System.Random(seed);
            var lips = new float[32];
            for (int i = 0; i < lips.Length; i++) lips[i] = (float)rnd.NextDouble() * 0.05f - 0.03f;
            var ys = new List<float> { h, h - 0.4f };
            for (float y = h - 1.5f; y > -1.5f; y -= 2.2f) ys.Add(y);
            ys.Add(-1.5f);
            var v = new List<Vector3>(); var col = new List<Color>(); var side = new List<int>(); var cap = new List<int>();
            Vector3 Ring(float a, float k, float y)
            {
                float ca = Mathf.Cos(a), sa = Mathf.Sin(a);
                float sx = Mathf.Sign(ca) * Mathf.Pow(Mathf.Abs(ca), 0.5f), sz = Mathf.Sign(sa) * Mathf.Pow(Mathf.Abs(sa), 0.5f);   // superellipse, power 4
                return new Vector3(centre.x + sx * hx * k, y, centre.z + sz * hz * k);
            }
            for (int j = 0; j < ys.Count; j++)
            {
                float y = ys[j], depth = h - y;
                int layer = Mathf.FloorToInt(depth / 2.6f);
                float lip = j < 2 ? 0f : lips[layer % lips.Length];
                float flare = 1f + 0.08f * Mathf.Clamp01(depth / Mathf.Max(h, 1f));
                for (int i = 0; i <= seg; i++)
                {
                    float a = i * Mathf.PI * 2f / seg;
                    float n = j < 2 ? -0.004f : (Mathf.PerlinNoise(Mathf.Cos(a) * 3f + seed, Mathf.Sin(a) * 3f + layer * 0.4f) - 0.5f) * 0.05f;
                    float k = (j == 0 ? 0.985f : 1f) * (flare + lip + n);
                    v.Add(Ring(a, k, y + (j > 1 ? (Mathf.PerlinNoise(a * 4f, depth) - 0.5f) * 0.8f : 0f)));
                    float under = j > 1 && depth % 2.6f < 1.0f ? 0.6f : 0.95f;
                    // The top ring is shared with the grass cap, painted for the ground shader (grass, a few flowers).
                    col.Add(j == 0 ? new Color(1f, 0f, 0f, 0.15f) : new Color(under, j == 1 ? 0.8f : 0.4f, 0f, 1f));
                }
            }
            for (int j = 0; j < ys.Count - 1; j++)
                for (int i = 0; i < seg; i++)
                {
                    int a0 = j * (seg + 1) + i, b0 = a0 + seg + 1;
                    side.AddRange(new[] { a0, a0 + 1, b0, a0 + 1, b0 + 1, b0 });
                }
            int centreIndex = v.Count;
            v.Add(new Vector3(centre.x, h + 0.05f, centre.z)); col.Add(new Color(1f, 0f, 0f, 0.15f));
            for (int i = 0; i < seg; i++) cap.AddRange(new[] { centreIndex, i + 1, i });
            var m = new Mesh { name = name, indexFormat = IndexFormat.UInt32, subMeshCount = 2 };
            m.SetVertices(v); m.SetColors(col);
            m.SetTriangles(side, 0); m.SetTriangles(cap, 1);
            m.RecalculateNormals(); m.RecalculateBounds();
            Directory.CreateDirectory(MeshDir);
            string path = $"{MeshDir}/{name}.asset";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = m;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterials = new[] { rock, grass };
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
            return go;
        }

        public static Mesh WheatClump()
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var c = new List<Color>(); var t = new List<int>();
            var rnd = new System.Random(5);
            for (int b = 0; b < 10; b++)
            {
                float a = (float)rnd.NextDouble() * Mathf.PI * 2f, r = (float)rnd.NextDouble() * 0.2f;
                var root = new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r);
                float height = 0.85f + (float)rnd.NextDouble() * 0.3f;
                float face = (float)rnd.NextDouble() * Mathf.PI * 2f;
                var side = new Vector3(Mathf.Cos(face), 0f, Mathf.Sin(face));
                var lean = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * 0.06f;
                var normal = Vector3.Cross(side, Vector3.up).normalized;
                int i = v.Count;
                float tone = (float)rnd.NextDouble();
                // a stalk, then a plump ear of grain at the top
                v.Add(root - side * 0.008f); v.Add(root + side * 0.008f);
                v.Add(root + lean * 0.8f + Vector3.up * height * 0.78f - side * 0.008f); v.Add(root + lean * 0.8f + Vector3.up * height * 0.78f + side * 0.008f);
                v.Add(root + lean * 0.85f + Vector3.up * height * 0.82f - side * 0.03f); v.Add(root + lean * 0.85f + Vector3.up * height * 0.82f + side * 0.03f);
                v.Add(root + lean + Vector3.up * height);
                foreach (float hh in new[] { 0f, 0f, 0.78f, 0.78f, 0.9f, 0.9f, 1f }) { n.Add(normal); c.Add(new Color(tone, 0f, 0f, hh)); }
                t.AddRange(new[] { i, i + 2, i + 1, i + 1, i + 2, i + 3, i + 2, i + 4, i + 3, i + 3, i + 4, i + 5, i + 4, i + 6, i + 5 });
            }
            var m = new Mesh { name = "WheatClump" };
            m.SetVertices(v); m.SetNormals(n); m.SetColors(c); m.SetTriangles(t, 0);
            m.RecalculateBounds();
            return m;
        }

        // ------------------------------------------------------------ grass and wildflower meshes
        public static Mesh GrassClump(bool flowers)
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var c = new List<Color>(); var t = new List<int>();
            var rnd = new System.Random(flowers ? 7 : 3);
            int blades = flowers ? 6 : 14;
            for (int b = 0; b < blades; b++)
            {
                float a = (float)rnd.NextDouble() * Mathf.PI * 2f, r = (float)rnd.NextDouble() * 0.16f;
                var root = new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r);
                float height = 0.22f + (float)rnd.NextDouble() * 0.26f, width = 0.014f + (float)rnd.NextDouble() * 0.012f;
                float face = (float)rnd.NextDouble() * Mathf.PI * 2f;
                var side = new Vector3(Mathf.Cos(face), 0f, Mathf.Sin(face)) * width;
                var lean = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a)) * (0.08f + (float)rnd.NextDouble() * 0.1f);
                var normal = Vector3.Cross(side, Vector3.up).normalized;
                int i = v.Count;
                float tone = (float)rnd.NextDouble();
                v.Add(root - side); v.Add(root + side); v.Add(root + lean * 0.5f + Vector3.up * height * 0.55f - side * 0.6f);
                v.Add(root + lean * 0.5f + Vector3.up * height * 0.55f + side * 0.6f); v.Add(root + lean + Vector3.up * height);
                foreach (float hh in new[] { 0f, 0f, 0.55f, 0.55f, 1f }) { n.Add(normal); c.Add(new Color(tone, 0f, 0f, hh)); }
                t.AddRange(new[] { i, i + 2, i + 1, i + 1, i + 2, i + 3, i + 2, i + 4, i + 3 });
            }
            if (flowers)
            {
                var heads = new[] { new Color(1f, 1f, 1f), new Color(0.96f, 0.6f, 0.76f), new Color(0.74f, 0.64f, 0.98f) };
                for (int f = 0; f < 3; f++)
                {
                    float a = f * 2.1f;
                    var p = new Vector3(Mathf.Cos(a) * 0.12f, 0.42f + f * 0.05f, Mathf.Sin(a) * 0.12f);
                    var col = heads[f % heads.Length]; col.a = 1f;
                    int i = v.Count;
                    for (int k = 0; k < 6; k++) { float q = k * Mathf.PI / 3f; v.Add(p + new Vector3(Mathf.Cos(q), 0f, Mathf.Sin(q)) * 0.05f); n.Add(Vector3.up); c.Add(col); }
                    v.Add(p + Vector3.up * 0.01f); n.Add(Vector3.up); c.Add(new Color(1f, 0.85f, 0.3f, 1f) * new Color(1, 1, 1, 1));
                    c[c.Count - 1] = new Color(1f, 0.85f, 0.6f, 1f);
                    for (int k = 0; k < 6; k++) t.AddRange(new[] { i + 6, i + (k + 1) % 6, i + k });
                }
            }
            var m = new Mesh { name = flowers ? "Wildflowers" : "GrassClump" };
            m.SetVertices(v); m.SetNormals(n); m.SetColors(c); m.SetTriangles(t, 0);
            m.RecalculateBounds();
            return m;
        }
    }
}

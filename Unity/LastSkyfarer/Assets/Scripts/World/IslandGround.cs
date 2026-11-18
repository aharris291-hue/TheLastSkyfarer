// The Last Skyfarer: Brindle Isle's ground (polish pass 1). Holds the island's height and paint grid (built in the
// editor by IslandTerrainBuilder: gentle rolling meadows, flat where buildings, paths and story places stand) and draws
// dense grass and wildflowers near the camera with GPU instancing. Grass is generated per 16 m cell from a hash, so
// it is the same every time, and it shrinks away towards the edge of its radius instead of popping.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace LastSkyfarer.World
{
    public class IslandGround : MonoBehaviour
    {
        public static IslandGround Current { get; private set; }

        [Header("Grid (filled by the builder)")]
        public Vector2 Origin;           // world x, z of grid cell (0, 0)
        public float Spacing = 3f;
        public int Width, Height;
        public float[] Heights = new float[0];
        public Color32[] Paint = new Color32[0];   // R grass, G dirt, B cobbles, A flowers

        [Header("Grass")]
        public Mesh GrassMesh, FlowerMesh;
        public Material GrassMaterial, FlowerMaterial;
        public float Radius = 40f;
        [Tooltip("Grass clumps per square metre on full grass.")] public float Density = 2.2f;
        public float CellSize = 16f;

        [Header("Wheat (Whispermill)")]
        public Mesh WheatMesh;
        public Material WheatMaterial;
        public List<Rect> WheatFields = new List<Rect>();          // world x, z
        public List<Vector3> WheatHoles = new List<Vector3>();      // x, z, radius: windmills and the like
        public float WheatDensity = 3.5f;

        [Header("Plateaus (grass grows on their tops too)")]
        public List<Vector4> Plateaus = new List<Vector4>();       // centre x, centre z, half width, half depth
        public List<float> PlateauHeights = new List<float>();
        public Vector2 IslandRadii = new Vector2(700f, 575f);

        readonly Dictionary<Vector2Int, Matrix4x4[]> grassCells = new Dictionary<Vector2Int, Matrix4x4[]>();
        readonly Dictionary<Vector2Int, Matrix4x4[]> flowerCells = new Dictionary<Vector2Int, Matrix4x4[]>();
        readonly Dictionary<Vector2Int, Matrix4x4[]> wheatCells = new Dictionary<Vector2Int, Matrix4x4[]>();
        readonly List<Matrix4x4> wheatBatch = new List<Matrix4x4>(1023);
        readonly List<Matrix4x4> grassBatch = new List<Matrix4x4>(1023), flowerBatch = new List<Matrix4x4>(1023);
        static readonly int FadeId = Shader.PropertyToID("_LS_GrassFade");

        void OnEnable() => Current = this;
        void OnDisable() { if (Current == this) Current = null; }

        public bool Inside(float x, float z) => Width > 1 && Height > 1;

        void Cell(float x, float z, out int ix, out int iz, out float fx, out float fz)
        {
            float gx = Mathf.Clamp((x - Origin.x) / Spacing, 0f, Width - 1.001f);
            float gz = Mathf.Clamp((z - Origin.y) / Spacing, 0f, Height - 1.001f);
            ix = (int)gx; iz = (int)gz; fx = gx - ix; fz = gz - iz;
        }

        public float HeightAt(float x, float z)
        {
            for (int pi = 0; pi < Plateaus.Count; pi++)
            {
                var p = Plateaus[pi];
                if (Mathf.Abs(x - p.x) < p.z * 0.95f && Mathf.Abs(z - p.y) < p.w * 0.95f) return PlateauHeights[pi];
            }
            if (Heights.Length == 0) return 0f;
            Cell(x, z, out int ix, out int iz, out float fx, out float fz);
            int i = iz * Width + ix;
            float a = Mathf.Lerp(Heights[i], Heights[i + 1], fx), b = Mathf.Lerp(Heights[i + Width], Heights[i + Width + 1], fx);
            return Mathf.Lerp(a, b, fz);
        }

        public Color PaintAt(float x, float z)
        {
            if (Paint.Length == 0) return new Color(1, 0, 0, 0);
            Cell(x, z, out int ix, out int iz, out float fx, out float fz);
            int i = iz * Width + ix;
            Color a = Color.Lerp(Paint[i], Paint[i + 1], fx), b = Color.Lerp(Paint[i + Width], Paint[i + Width + 1], fx);
            return Color.Lerp(a, b, fz);
        }

        static float Hash(int x, int y, int k)
        {
            uint h = (uint)(x * 73856093) ^ (uint)(y * 19349663) ^ (uint)(k * 83492791);
            h ^= h >> 13; h *= 0x5bd1e995; h ^= h >> 15;
            return (h & 0xFFFFFF) / 16777215f;
        }

        void Build(Vector2Int c)
        {
            var grass = new List<Matrix4x4>();
            var flowers = new List<Matrix4x4>();
            int n = Mathf.RoundToInt(CellSize * CellSize * Density);
            for (int k = 0; k < n; k++)
            {
                float x = (c.x + Hash(c.x, c.y, k * 3)) * CellSize, z = (c.y + Hash(c.x, c.y, k * 3 + 1)) * CellSize;
                if ((x / IslandRadii.x) * (x / IslandRadii.x) + (z / IslandRadii.y) * (z / IslandRadii.y) > 0.95f) continue;   // never past the rim
                Color p = PaintAt(x, z);
                float keep = Hash(c.x, c.y, k * 3 + 2);
                if (keep > p.r * (1f - p.g) * (1f - p.b)) continue;           // grass only where the ground is grassy
                if (InWheat(x, z)) continue;                                   // the wheat field grows wheat instead
                float y = HeightAt(x, z);
                float s = 0.75f + Hash(c.x, c.y, k * 5 + 7) * 0.6f;
                var m = Matrix4x4.TRS(new Vector3(x, y - 0.02f, z), Quaternion.Euler(0f, keep * 3600f, 0f), new Vector3(s, s * (0.8f + p.r * 0.4f), s));
                if (Hash(c.x, c.y, k * 7 + 3) < p.a * 0.35f) flowers.Add(m); else grass.Add(m);
            }
            var wheat = new List<Matrix4x4>();
            if (WheatMesh)
            {
                int nw = Mathf.RoundToInt(CellSize * CellSize * WheatDensity);
                for (int k = 0; k < nw; k++)
                {
                    float x = (c.x + Hash(c.x, c.y, k * 3 + 90001)) * CellSize, z = (c.y + Hash(c.x, c.y, k * 3 + 90002)) * CellSize;
                    if (!InWheat(x, z)) continue;
                    float s = 0.85f + Hash(c.x, c.y, k * 5 + 90003) * 0.35f;
                    wheat.Add(Matrix4x4.TRS(new Vector3(x, HeightAt(x, z) + 0.28f, z), Quaternion.Euler(0f, Hash(c.x, c.y, k) * 360f, 0f), new Vector3(s, s, s)));
                }
            }
            wheatCells[c] = wheat.ToArray();
            grassCells[c] = grass.ToArray();
            flowerCells[c] = flowers.ToArray();
        }

        bool InWheat(float x, float z)
        {
            bool inside = false;
            foreach (var r in WheatFields) if (r.Contains(new Vector2(x, z))) { inside = true; break; }
            if (!inside) return false;
            foreach (var hole in WheatHoles) if ((new Vector2(x - hole.x, z - hole.y)).sqrMagnitude < hole.z * hole.z) return false;
            return true;
        }

        void Update()
        {
            var cam = Camera.main;
            if (!cam || !GrassMesh || !GrassMaterial || Heights.Length == 0) return;
            Vector3 p = cam.transform.position;
            float ground = HeightAt(p.x, p.z);
            if (p.y - ground > Radius) return;                                 // high in the air: no grass to see
            Shader.SetGlobalVector(FadeId, new Vector4(p.x, p.y, p.z, Radius));
            int r = Mathf.CeilToInt(Radius / CellSize);
            var cc = new Vector2Int(Mathf.FloorToInt(p.x / CellSize), Mathf.FloorToInt(p.z / CellSize));
            grassBatch.Clear(); flowerBatch.Clear(); wheatBatch.Clear();
            var planes = GeometryUtility.CalculateFrustumPlanes(cam);
            for (int dz = -r; dz <= r; dz++)
                for (int dx = -r; dx <= r; dx++)
                {
                    var c = new Vector2Int(cc.x + dx, cc.y + dz);
                    var centre = new Vector3((c.x + 0.5f) * CellSize, HeightAt((c.x + 0.5f) * CellSize, (c.y + 0.5f) * CellSize), (c.y + 0.5f) * CellSize);
                    if (Vector2.Distance(new Vector2(centre.x, centre.z), new Vector2(p.x, p.z)) > Radius + CellSize * 0.75f) continue;
                    if (!GeometryUtility.TestPlanesAABB(planes, new Bounds(centre, new Vector3(CellSize, 8f, CellSize)))) continue;
                    if (!grassCells.ContainsKey(c)) Build(c);
                    Add(grassBatch, grassCells[c], GrassMesh, GrassMaterial);
                    if (FlowerMesh && FlowerMaterial) Add(flowerBatch, flowerCells[c], FlowerMesh, FlowerMaterial);
                    if (WheatMesh && WheatMaterial) Add(wheatBatch, wheatCells[c], WheatMesh, WheatMaterial);
                }
            Flush(grassBatch, GrassMesh, GrassMaterial);
            Flush(flowerBatch, FlowerMesh, FlowerMaterial);
            Flush(wheatBatch, WheatMesh, WheatMaterial);
        }

        void Add(List<Matrix4x4> batch, Matrix4x4[] items, Mesh mesh, Material mat)
        {
            foreach (var m in items)
            {
                batch.Add(m);
                if (batch.Count == 1023) Flush(batch, mesh, mat);
            }
        }

        static void Flush(List<Matrix4x4> batch, Mesh mesh, Material mat)
        {
            if (batch.Count == 0 || !mesh || !mat) { batch.Clear(); return; }
            var rp = new RenderParams(mat) { shadowCastingMode = ShadowCastingMode.Off, receiveShadows = true };
            Graphics.RenderMeshInstanced(rp, mesh, 0, batch);
            batch.Clear();
        }
    }
}

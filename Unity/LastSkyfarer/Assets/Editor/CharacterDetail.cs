// The Last Skyfarer: character pass. Grows hand-styled hair cards and adds proper eyes to a character, from the
// character's own bake: the hair/skin/eye mask tells where hair and eyes are, the colour atlas gives each card its
// colour. Everything is built at the bind pose in the head bone's space and parented to the head, so it moves with
// him. Called by KieranSetup and VillagerSetup.
//   Hair: alpha-cut strand cards (curly or straight strand textures generated here), each a three-row ribbon that
//   arches away from the head and droops at the tip; styles per character (tight curl tufts, long falling curls,
//   combed back, beard).
//   Eyes: a glossy cornea dome over each painted eye and a thin wet line along the lower lid.
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace LastSkyfarer.EditorTools
{
    public enum HairStyle { CurlTufts, CurlsLong, CurlsMedium, CombedBack, CombedShort }

    public static class CharacterDetail
    {
        const string SharedDir = "Assets/Art/Characters/Shared";

        public static Material HairMaterial(bool curly)
        {
            Directory.CreateDirectory(SharedDir);
            string tex = $"{SharedDir}/T_Hair{(curly ? "Curly" : "Straight")}.png";
            if (true)
            {
                File.WriteAllBytes(tex, StrandTexture(curly).EncodeToPNG());
                AssetDatabase.ImportAsset(tex);
                var ti = (TextureImporter)AssetImporter.GetAtPath(tex);
                ti.alphaIsTransparency = true;
                ti.mipMapsPreserveCoverage = true;
                ti.alphaTestReferenceValue = 0.45f;
                ti.wrapMode = TextureWrapMode.Clamp;
                ti.sRGBTexture = true;
                ti.SaveAndReimport();
            }
            string path = $"{SharedDir}/M_Hair{(curly ? "Curly" : "Straight")}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("LastSkyfarer/HairCards")); AssetDatabase.CreateAsset(m, path); }
            m.shader = Shader.Find("LastSkyfarer/HairCards");
            m.SetTexture("_StrandMap", AssetDatabase.LoadAssetAtPath<Texture2D>(tex));
            m.SetFloat("_Cutoff", 0.45f);
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            return m;
        }

        static Material EyeMaterial(bool wet)
        {
            Directory.CreateDirectory(SharedDir);
            string path = $"{SharedDir}/M_Eye{(wet ? "WetLine" : "Cornea")}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(Shader.Find("LastSkyfarer/EyeCornea")); AssetDatabase.CreateAsset(m, path); }
            m.shader = Shader.Find("LastSkyfarer/EyeCornea");
            m.SetFloat("_Wet", wet ? 1f : 0f);
            EditorUtility.SetDirty(m);
            return m;
        }

        /// <summary>Strand clumps painted into a 512 x 512 texture: alpha is the strand, red its shade.</summary>
        static Texture2D StrandTexture(bool curly)
        {
            const int S = 512;
            var px = new Color[S * S];
            var rnd = new System.Random(curly ? 11 : 13);
            int strands = curly ? 80 : 120;
            for (int k = 0; k < strands; k++)
            {
                float x0 = 20f + (float)rnd.NextDouble() * (S - 40);
                float width = curly ? 5f + (float)rnd.NextDouble() * 4f : 3f + (float)rnd.NextDouble() * 2.5f;
                float amp = curly ? 14f + (float)rnd.NextDouble() * 10f : 1.5f + (float)rnd.NextDouble() * 2f;
                float freq = curly ? 3.5f + (float)rnd.NextDouble() * 2f : 0.6f;
                float phase = (float)rnd.NextDouble() * 6.28f;
                float shade = 0.45f + (float)rnd.NextDouble() * 0.55f;
                float len = 0.75f + (float)rnd.NextDouble() * 0.25f;
                for (int y = 0; y < S; y++)
                {
                    float v = y / (float)S;
                    if (v > len) break;
                    float taper = 1f - Mathf.Pow(v / len, 2f) * 0.85f;
                    float cx = x0 + Mathf.Sin(v * freq * Mathf.PI * 2f + phase) * amp * (curly ? (0.6f + 0.4f * v) : 1f);
                    float w = width * taper;
                    for (int x = Mathf.Max(0, (int)(cx - w - 2)); x <= Mathf.Min(S - 1, (int)(cx + w + 2)); x++)
                    {
                        float d = Mathf.Abs(x - cx) / Mathf.Max(w, 0.5f);
                        float a = Mathf.Clamp01(1.4f - d);
                        int i = y * S + x;
                        if (a > px[i].a) px[i] = new Color(shade * (0.85f + 0.15f * (1f - d)), 0f, 0f, a);
                    }
                }
            }
            var t = new Texture2D(S, S, TextureFormat.RGBA32, true);
            t.SetPixels(px);
            t.Apply();
            return t;
        }

        struct Sample { public Vector3 p, n; public Vector2 uv; }

        /// <summary>Reads a PNG straight from disk (readable, without making the imported 4K texture readable in the game).</summary>
        public static Texture2D LoadPng(string path)
        {
            var t = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            t.LoadImage(File.ReadAllBytes(path));
            return t;
        }

        public static void Build(GameObject model, Animator anim, string name, string dir, Texture2D colour, Texture2D mask, HairStyle style, bool beard, float eyeScale = 1f)
        {
            var smr = model.GetComponentInChildren<SkinnedMeshRenderer>();
            var head = anim.GetBoneTransform(HumanBodyBones.Head);
            var baked = new Mesh();
            smr.BakeMesh(baked, true);
            var verts = baked.vertices; var norms = baked.normals; var uvs = baked.uv;
            var hair = new List<Sample>(); var eyes = new List<Sample>();
            Vector3 hp = head.position;
            for (int i = 0; i < verts.Length; i++)
            {
                Vector3 w = smr.transform.TransformPoint(verts[i]);
                if ((w - hp).magnitude > 0.32f) continue;
                Color m = mask.GetPixelBilinear(uvs[i].x, uvs[i].y);
                var s = new Sample { p = w, n = smr.transform.TransformDirection(norms[i]).normalized, uv = uvs[i] };
                if (m.r > 0.5f) hair.Add(s);
                else if (m.b > 0.5f) eyes.Add(s);
            }
            // Eye level: the painted eyes (or a fallback above the head bone).
            float eyeY = hp.y + 0.09f;
            if (eyes.Count > 0) { eyeY = 0f; foreach (var e in eyes) eyeY += e.p.y; eyeY /= eyes.Count; }

            var root = new GameObject("CharacterDetail").transform;
            root.SetParent(head, false);
            int cards = BuildHair(root, name, dir, hair, colour, style, beard, eyeY, hp);
            int eyeParts = BuildEyes(root, name, dir, eyes, eyeScale);
            Debug.Log($"LS_DETAIL {name}: {hair.Count} hair samples -> {cards} cards; {eyes.Count} eye samples -> {eyeParts} eye parts");
        }

        static int BuildHair(Transform parent, string name, string dir, List<Sample> hair, Texture2D colour, HairStyle style, bool beard, float eyeY, Vector3 hp)
        {
            if (hair.Count == 0) return 0;
            var rnd = new System.Random(name.GetHashCode());
            bool curly = style == HairStyle.CurlTufts || style == HairStyle.CurlsLong || style == HairStyle.CurlsMedium;
            int target = style == HairStyle.CurlTufts ? 1600 : style == HairStyle.CurlsLong ? 1300 : style == HairStyle.CurlsMedium ? 1200 : style == HairStyle.CombedBack ? 800 : 600;
            var headCards = new MeshBuilder(); var beardCards = new MeshBuilder();
            int made = 0;
            // The character's overall hair colour: each card is pulled towards it, so stray atlas texels (skin, cloth,
            // painted highlights) never become pale shards in dark hair.
            Color avg = Color.black;
            foreach (var h in hair) avg += colour.GetPixelBilinear(h.uv.x, h.uv.y);
            avg /= hair.Count;
            for (int k = 0; k < target * 2 && made < target; k++)
            {
                var s = hair[rnd.Next(hair.Count)];
                bool isBeard = s.p.y < eyeY - 0.045f && s.p.z > hp.z + 0.02f;
                if (isBeard && !beard) continue;
                // Never grow from the eyebrows or lashes, and never over the face.
                if (s.p.y > eyeY - 0.035f && s.p.y < eyeY + 0.045f && s.p.z > hp.z + 0.04f) continue;
                if (!isBeard && s.p.z > hp.z + 0.06f && s.p.y < eyeY + 0.07f) continue;
                Color c = (Color.Lerp(avg, colour.GetPixelBilinear(s.uv.x, s.uv.y), 0.3f) * (0.88f + (float)rnd.NextDouble() * 0.24f)).linear;   // vertex colours are linear
                c.a = 1f;
                Vector3 n = s.n, d; float len, wid; Vector3 rand = new Vector3((float)rnd.NextDouble() - 0.5f, (float)rnd.NextDouble() - 0.5f, (float)rnd.NextDouble() - 0.5f);
                Vector3 back = new Vector3(0f, 0f, -1f), down = Vector3.down;
                Vector3 tang = rand - n * Vector3.Dot(rand, n);
                if (tang.sqrMagnitude < 1e-4f) tang = Vector3.Cross(n, Vector3.up);
                tang.Normalize();
                float droop;
                if (isBeard)
                {
                    d = (down * 0.85f + Vector3.forward * 0.2f + n * 0.25f + rand * 0.2f).normalized; len = 0.018f + (float)rnd.NextDouble() * 0.02f; wid = 0.024f; droop = 0.1f;
                }
                else switch (style)
                {
                    case HairStyle.CurlTufts:
                        d = (n * 0.4f + tang * 0.9f).normalized; len = 0.024f + (float)rnd.NextDouble() * 0.018f; wid = 0.04f; droop = 0.02f; break;
                    case HairStyle.CurlsLong:
                        d = (s.p.y > eyeY + 0.07f ? back * 0.6f + down * 0.4f + n * 0.25f + tang * 0.3f : down * 0.85f + n * 0.25f + tang * 0.2f); d.Normalize();
                        len = s.p.y > eyeY + 0.07f ? 0.06f + (float)rnd.NextDouble() * 0.04f : 0.12f + (float)rnd.NextDouble() * 0.08f; wid = 0.045f; droop = 0.2f; break;
                    case HairStyle.CurlsMedium:
                        d = (n * 0.35f + down * 0.5f + back * 0.2f + tang * 0.4f).normalized; len = 0.045f + (float)rnd.NextDouble() * 0.03f; wid = 0.04f; droop = 0.12f; break;
                    case HairStyle.CombedBack:
                        d = back * 0.8f + down * 0.35f; d = (d - n * Vector3.Dot(d, n)).normalized; d = (d + n * 0.12f + rand * 0.15f).normalized;
                        len = 0.05f + (float)rnd.NextDouble() * 0.04f; wid = 0.03f; droop = 0.08f; break;
                    default:
                        d = back * 0.6f + down * 0.6f; d = (d - n * Vector3.Dot(d, n)).normalized; d = (d + n * 0.1f + rand * 0.15f).normalized;
                        len = 0.025f + (float)rnd.NextDouble() * 0.02f; wid = 0.026f; droop = 0.05f; break;
                }
                Vector3 side = Vector3.Cross(d, n);
                if (side.sqrMagnitude < 0.05f) side = Vector3.Cross(d, rand.normalized);
                side.Normalize();
                var mb = isBeard ? beardCards : headCards;
                float u0 = (float)rnd.NextDouble() * 0.7f;
                mb.Card(parent, s.p - n * 0.003f, d, n, side, len, wid, droop, c, u0, u0 + 0.3f);
                made++;
            }
            AddMesh(parent, $"{dir}/{name}_HairCards.asset", "HairCards", headCards, HairMaterial(curly), ShadowCastingMode.Off);   // cards shading each other turned light hair grey
            if (beardCards.Count > 0) AddMesh(parent, $"{dir}/{name}_BeardCards.asset", "BeardCards", beardCards, HairMaterial(false), ShadowCastingMode.Off);
            return made;
        }

        static int BuildEyes(Transform parent, string name, string dir, List<Sample> eyes, float eyeScale)
        {
            if (eyes.Count < 8) return 0;
            int parts = 0;
            var cornea = new MeshBuilder(); var wet = new MeshBuilder();
            foreach (float side in new[] { -1f, 1f })
            {
                var pts = eyes.FindAll(e => Mathf.Sign(e.p.x - parent.position.x) == side);
                if (pts.Count < 4) continue;
                Vector3 mean = Vector3.zero; foreach (var e in pts) mean += e.p; mean /= pts.Count;
                float halfW = 0f, front = float.MinValue;
                foreach (var e in pts) { halfW = Mathf.Max(halfW, Mathf.Abs(e.p.x - mean.x)); front = Mathf.Max(front, e.p.z); }
                float r = Mathf.Clamp(halfW, 0.008f, 0.016f) * eyeScale;
                var centre = new Vector3(mean.x, mean.y, front - r);
                cornea.SphereCap(parent, centre + Vector3.forward * r * 0.04f, r * 1.07f, 62f);
                wet.LidLine(parent, centre, r * 1.04f);
                parts += 2;
            }
            AddMesh(parent, $"{dir}/{name}_Cornea.asset", "Cornea", cornea, EyeMaterial(false), ShadowCastingMode.Off);
            AddMesh(parent, $"{dir}/{name}_WetLine.asset", "WetLine", wet, EyeMaterial(true), ShadowCastingMode.Off);
            return parts;
        }

        static void AddMesh(Transform parent, string path, string name, MeshBuilder mb, Material mat, ShadowCastingMode shadows = ShadowCastingMode.On)
        {
            if (mb.Count == 0) return;
            var mesh = mb.ToMesh(name);
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(mesh, path);
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = mat;
            mr.shadowCastingMode = shadows;
        }

        /// <summary>Collects geometry in the parent's (head bone's) space.</summary>
        class MeshBuilder
        {
            readonly List<Vector3> v = new List<Vector3>(), n = new List<Vector3>();
            readonly List<Vector4> t = new List<Vector4>();
            readonly List<Vector2> uv = new List<Vector2>();
            readonly List<Color> c = new List<Color>();
            readonly List<int> tri = new List<int>();
            public int Count => tri.Count;

            public void Card(Transform space, Vector3 rootW, Vector3 dirW, Vector3 normalW, Vector3 sideW, float len, float wid, float droop, Color col, float u0, float u1)
            {
                int b = v.Count;
                Vector3 cardN = Vector3.Cross(sideW, dirW).normalized;
                if (Vector3.Dot(cardN, normalW) < 0f) cardN = -cardN;
                for (int row = 0; row < 3; row++)
                {
                    float f = row / 2f;
                    Vector3 centre = rootW + dirW * len * f + normalW * len * 0.18f * Mathf.Sin(f * Mathf.PI) + Vector3.down * len * droop * f * f;
                    float w = wid * (1f - 0.45f * f);
                    foreach (float s in new[] { -0.5f, 0.5f })
                    {
                        v.Add(space.InverseTransformPoint(centre + sideW * w * s));
                        n.Add(space.InverseTransformDirection(cardN));
                        Vector3 tl = space.InverseTransformDirection(dirW);
                        t.Add(new Vector4(tl.x, tl.y, tl.z, 1f));
                        uv.Add(new Vector2(s < 0 ? u0 : u1, f));
                        c.Add(col);
                    }
                }
                for (int row = 0; row < 2; row++)
                {
                    int a = b + row * 2;
                    tri.AddRange(new[] { a, a + 2, a + 1, a + 1, a + 2, a + 3 });
                }
            }

            public void SphereCap(Transform space, Vector3 centreW, float r, float maxAngle)
            {
                int b = v.Count, rings = 6, segs = 16;
                for (int i = 0; i <= rings; i++)
                {
                    float phi = maxAngle * Mathf.Deg2Rad * i / rings;
                    for (int j = 0; j <= segs; j++)
                    {
                        float th = j * Mathf.PI * 2f / segs;
                        var dir = new Vector3(Mathf.Sin(phi) * Mathf.Cos(th), Mathf.Sin(phi) * Mathf.Sin(th), Mathf.Cos(phi));
                        v.Add(space.InverseTransformPoint(centreW + dir * r));
                        n.Add(space.InverseTransformDirection(dir));
                        t.Add(new Vector4(1, 0, 0, 1)); uv.Add(Vector2.zero); c.Add(Color.white);
                    }
                }
                for (int i = 0; i < rings; i++)
                    for (int j = 0; j < segs; j++)
                    {
                        int a = b + i * (segs + 1) + j, d = a + segs + 1;
                        tri.AddRange(new[] { a, d, a + 1, a + 1, d, d + 1 });
                    }
            }

            /// <summary>A thin moist band along the bottom of the eye opening.</summary>
            public void LidLine(Transform space, Vector3 centreW, float r)
            {
                int b = v.Count, segs = 10;
                for (int j = 0; j <= segs; j++)
                {
                    float th = Mathf.Lerp(200f, 340f, j / (float)segs) * Mathf.Deg2Rad;
                    foreach (float phi in new[] { 48f, 56f })
                    {
                        float p = phi * Mathf.Deg2Rad;
                        var dir = new Vector3(Mathf.Sin(p) * Mathf.Cos(th), Mathf.Sin(p) * Mathf.Sin(th), Mathf.Cos(p));
                        v.Add(space.InverseTransformPoint(centreW + dir * r));
                        n.Add(space.InverseTransformDirection(dir));
                        t.Add(new Vector4(1, 0, 0, 1)); uv.Add(Vector2.zero); c.Add(Color.white);
                    }
                }
                for (int j = 0; j < segs; j++)
                {
                    int a = b + j * 2;
                    tri.AddRange(new[] { a, a + 2, a + 1, a + 1, a + 2, a + 3 });
                }
            }

            public Mesh ToMesh(string name)
            {
                var m = new Mesh { name = name, indexFormat = v.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                m.SetVertices(v); m.SetNormals(n); m.SetTangents(t); m.SetUVs(0, uv); m.SetColors(c); m.SetTriangles(tri, 0);
                m.RecalculateBounds();
                return m;
            }
        }
    }
}

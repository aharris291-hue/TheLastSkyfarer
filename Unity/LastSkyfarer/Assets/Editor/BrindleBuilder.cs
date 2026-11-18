// The Last Skyfarer: builds Brindle Isle (Assets/Scenes/Brindle.unity) from our own data, in batchmode:
//   Unity.exe -batchmode -projectPath <project> -executeMethod LastSkyfarer.EditorTools.BrindleBuilder.Run -quit
// Inputs: Assets/Art/Brindle/BrindleLayout.json (exported from Unreal/Tools/build_brindle_greybox.py by
// Unity/Tools/layout/export_brindle_layout.py), Resources/Story/Interactions.json, the Windrest kit FBX files and
// the painterly material table below (Unreal/Tools/build_materials.py values, D-27).
// Greybox shapes keep the collision gameplay was built on (hidden where a kit piece shows instead); kit pieces are
// visual only, static-batched, and small ones stop drawing at a distance (layers Cull110 ... Cull650) for Low.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using LastSkyfarer.World;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using Object = UnityEngine.Object;

namespace LastSkyfarer.EditorTools
{
    public static class BrindleBuilder
    {
        public const string ScenePath = "Assets/Scenes/Brindle.unity";
        const string LayoutPath = "Assets/Art/Brindle/BrindleLayout.json";
        const string MatDir = "Assets/Art/Materials";
        const string GenDir = "Assets/Art/Generated";
        const string KitDir = "Assets/Art/Windrest/Meshes";
        const string KitPrefabDir = "Assets/Art/Windrest/Prefabs";
        const string NoisePath = "Assets/Art/Textures/T_BrushNoise.png";
        static readonly string[] CullLayers = { "Cull110", "Cull160", "Cull260", "Cull450", "Cull650" };
        static readonly float[] CullDistances = { 110f, 160f, 260f, 450f, 650f };

        // ------------------------------------------------------------ layout file types
        [Serializable] class V { public float x, y, z; public Vector3 ToV() => new Vector3(x, y, z); }
        [Serializable]
        class Item
        {
            public string Name, Folder, Kind, Mesh, Material, WindType, Id, Quest, Objective;
            public V Pos, Euler, Scale;
            public bool Hidden, Collider, Climbable, Shadow, StartsHidden;
            public float Spin, Cull, Strength, Radius;
            public List<string> Tags = new List<string>();
            public List<V> Points = new List<V>();
        }
        [Serializable] class Layout { public List<Item> Items = new List<Item>(); }

        // ------------------------------------------------------------ painterly materials (build_materials.py)
        class Paint
        {
            public string Shader = "LastSkyfarer/Painterly";
            public bool Foliage;
            public string A = "#B9A58A", B = "#9C8569", TopA = "#7FA548", TopB = "#5E8A3A";
            public float BrushScale = 4f, StrokeMix = 0.4f, TopAmount = 0f, TopStart = 0.6f, ShadeBottom = -120f, ShadeRange = 120f, ShadeAmount = 0.65f;
            public float WindAmountCm = 8f, WindSpeed = 1.3f, SwayHeight = 4f;
            public string Emission;
            public float Spec = 0.06f, Gloss = 20f, Rim = 0.22f, Bump = 0.6f;   // polish pass 1
        }
        static readonly Dictionary<string, Paint> Paints = new Dictionary<string, Paint>
        {
            ["MI_IslandGround"] = new Paint { Bump = 0.9f, A = "#A99278", B = "#86705B", TopA = "#86AE4C", TopB = "#5F8F3C", TopAmount = 1f, BrushScale = 9f },
            ["MI_CliffRock"] = new Paint { Bump = 1.3f, Rim = 0.15f, A = "#8E7C6B", B = "#6E5F55", BrushScale = 14f, ShadeBottom = -200f, ShadeRange = 160f, ShadeAmount = 0.55f },
            ["MI_Stone"] = new Paint { Bump = 1.0f, Spec = 0.05f, A = "#CDBB9C", B = "#AD9877", TopA = "#86AE4C", TopB = "#5F8F3C", TopAmount = 0.25f, BrushScale = 2f },
            ["MI_PathStone"] = new Paint { Bump = 1.0f, A = "#C9B596", B = "#A8916F", BrushScale = 1.5f, StrokeMix = 0.2f },
            ["MI_PathDirt"] = new Paint { A = "#B4936A", B = "#987A55", BrushScale = 2.5f },
            ["MI_Wood"] = new Paint { Bump = 0.9f, Spec = 0.08f, Gloss = 16f, A = "#8F6A45", B = "#6E4E33", BrushScale = 1f, StrokeMix = 0.85f },
            ["MI_WoodFloor"] = new Paint { Bump = 0.8f, Spec = 0.1f, A = "#9A7650", B = "#7A5A3C", BrushScale = 1.2f, StrokeMix = 0.9f },
            ["MI_Plaster"] = new Paint { Bump = 0.5f, Spec = 0.04f, A = "#EFE3C8", B = "#DCCBA8", BrushScale = 2f, ShadeAmount = 0.85f },
            ["MI_RoofTerracotta"] = new Paint { Bump = 0.8f, Spec = 0.12f, Gloss = 24f, A = "#C8693F", B = "#A9512F", BrushScale = 1.5f, StrokeMix = 0.7f },
            ["MI_RoofBlue"] = new Paint { Bump = 0.8f, Spec = 0.14f, Gloss = 28f, A = "#4F86B8", B = "#3B6A96", BrushScale = 1.5f, StrokeMix = 0.7f },
            ["MI_RoofGreen"] = new Paint { Bump = 0.8f, Spec = 0.12f, Gloss = 24f, A = "#6F9A5A", B = "#557D45", BrushScale = 1.5f, StrokeMix = 0.7f },
            ["MI_Sailcloth"] = new Paint { Bump = 0.4f, Spec = 0.03f, Rim = 0.3f, A = "#EDE1C6", B = "#D6C49F", BrushScale = 3f, StrokeMix = 0.8f },
            ["MI_Brass"] = new Paint { Bump = 0.2f, Spec = 0.7f, Gloss = 60f, Rim = 0.35f, A = "#C79A3B", B = "#A57C2C", BrushScale = 0.6f },
            ["MI_LanternGlow"] = new Paint { Bump = 0.2f, Spec = 0.6f, Gloss = 60f, A = "#B98E52", B = "#9A7140", BrushScale = 0.6f, Emission = "#000000" },
            ["MI_Foliage"] = new Paint { Bump = 0.7f, Spec = 0.05f, Rim = 0.4f, Foliage = true, A = "#6E9C44", B = "#4E7A33", BrushScale = 3f, ShadeBottom = -10f, ShadeRange = 20f, ShadeAmount = 0.8f },
            ["MI_FoliageBlossom"] = new Paint { Bump = 0.7f, Spec = 0.05f, Rim = 0.4f, Foliage = true, A = "#8DB255", B = "#E7A6B8", BrushScale = 2f, StrokeMix = 0.2f, ShadeAmount = 0.85f },
            ["MI_Wheat"] = new Paint { Bump = 0.5f, Rim = 0.4f, Foliage = true, A = "#E2BE5E", B = "#C99A3E", BrushScale = 3f, WindAmountCm = 4f, WindSpeed = 1.8f, SwayHeight = 0.3f },
            ["MI_Water"] = new Paint { Bump = 0.4f, Spec = 0.9f, Gloss = 140f, Rim = 0.4f, A = "#7CC3DE", B = "#4E98BE", BrushScale = 0.8f, StrokeMix = 0.6f, ShadeAmount = 0.9f },
            ["MI_Grass"] = new Paint { Bump = 0.4f, Rim = 0.35f, Foliage = true, A = "#8DB651", B = "#5F8F3C", BrushScale = 1.5f, WindAmountCm = 6f, WindSpeed = 1.6f, ShadeAmount = 0.9f, SwayHeight = 0.8f },
            ["MI_FlowerBed"] = new Paint { Bump = 0.4f, Rim = 0.3f, Foliage = true, A = "#E77FA0", B = "#F2C84B", BrushScale = 0.5f, StrokeMix = 0.1f, WindAmountCm = 2f, SwayHeight = 0.6f },
            ["MI_Burlap"] = new Paint { Bump = 0.9f, Spec = 0.02f, A = "#B79B6B", B = "#9C805A", BrushScale = 0.6f, StrokeMix = 0.7f },
            ["MI_Hay"] = new Paint { Bump = 1.0f, Spec = 0.03f, A = "#E0C46A", B = "#C7A44C", BrushScale = 0.4f, StrokeMix = 0.9f },
            ["MI_Cloth_Red"] = new Paint { Bump = 0.3f, Spec = 0.03f, Rim = 0.3f, A = "#C8553D", B = "#A8402E", BrushScale = 1.2f, StrokeMix = 0.6f },
            ["MI_Cloth_Blue"] = new Paint { Bump = 0.3f, Spec = 0.03f, Rim = 0.3f, A = "#4F7FB8", B = "#3D6799", BrushScale = 1.2f, StrokeMix = 0.6f },
            ["MI_Cloth_Yellow"] = new Paint { Bump = 0.3f, Spec = 0.03f, Rim = 0.3f, A = "#E8C24A", B = "#D1A53A", BrushScale = 1.2f, StrokeMix = 0.6f },
            ["MI_Glass"] = new Paint { Bump = 0.0f, Spec = 1.0f, Gloss = 160f, Rim = 0.5f, A = "#2F4A58", B = "#3A5A6A", BrushScale = 0.5f, StrokeMix = 0.2f, ShadeAmount = 1f },
            ["MI_NotePaper"] = new Paint { A = "#F6EBD2", B = "#E8D7B2", BrushScale = 0.4f, Emission = "#3A2E1A" },
        };
        static readonly Dictionary<string, Material> Mats = new Dictionary<string, Material>();
        static Texture2D noise;

        static Color Hex(string h) => ColorUtility.TryParseHtmlString(h, out var c) ? c : Color.magenta;

        public static void Run()
        {
            RenderingSetup.Run();
            EnsureLayers();
            PrepareNoise();
            BuildMaterials();
            var meshes = BuildMeshes();
            var kit = BuildKitPrefabs();
            BuildScene(meshes, kit);
            Debug.Log("LS_BRINDLE_BUILD_OK");
        }

        // ------------------------------------------------------------ project setup
        static void EnsureLayers()
        {
            var tm = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset")[0]);
            var layers = tm.FindProperty("layers");
            for (int i = 0; i < CullLayers.Length; i++) layers.GetArrayElementAtIndex(BrindleLevel.FirstCullLayer + i).stringValue = CullLayers[i];
            tm.ApplyModifiedPropertiesWithoutUndo();
        }

        static void PrepareNoise()
        {
            var ti = (TextureImporter)AssetImporter.GetAtPath(NoisePath);
            if (ti.sRGBTexture || ti.wrapMode != TextureWrapMode.Repeat)
            {
                ti.sRGBTexture = false;           // a mask, like SAMPLERTYPE_MASKS in Unreal
                ti.wrapMode = TextureWrapMode.Repeat;
                ti.mipmapEnabled = true;
                ti.textureCompression = TextureImporterCompression.CompressedHQ;
                ti.SaveAndReimport();
            }
            noise = AssetDatabase.LoadAssetAtPath<Texture2D>(NoisePath);
        }

        static Material SaveMat(string name, Shader shader)
        {
            Directory.CreateDirectory(MatDir);
            string path = $"{MatDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!m) { m = new Material(shader); AssetDatabase.CreateAsset(m, path); }
            m.shader = shader;
            Mats[name] = m;
            return m;
        }

        static void BuildMaterials()
        {
            var painterly = Shader.Find("LastSkyfarer/Painterly");
            foreach (var kv in Paints)
            {
                var p = kv.Value;
                var m = SaveMat(kv.Key, painterly);
                m.SetTexture("_BrushNoise", noise);
                m.SetColor("_ColorA", Hex(p.A)); m.SetColor("_ColorB", Hex(p.B));
                m.SetColor("_TopColorA", Hex(p.TopA)); m.SetColor("_TopColorB", Hex(p.TopB));
                m.SetFloat("_TopAmount", p.TopAmount); m.SetFloat("_TopStart", p.TopStart);
                m.SetFloat("_BrushScale", p.BrushScale); m.SetFloat("_StrokeMix", p.StrokeMix);
                m.SetFloat("_ShadeBottom", p.ShadeBottom); m.SetFloat("_ShadeRange", p.ShadeRange); m.SetFloat("_ShadeAmount", p.ShadeAmount);
                m.SetFloat("_WindAmount", p.Foliage ? p.WindAmountCm / 100f : 0f); m.SetFloat("_WindSpeed", p.WindSpeed); m.SetFloat("_SwayHeight", p.SwayHeight);
                m.SetColor("_Emission", p.Emission != null ? Hex(p.Emission) : Color.black);
                m.SetFloat("_Specular", p.Spec); m.SetFloat("_Gloss", p.Gloss); m.SetFloat("_Rim", p.Rim); m.SetFloat("_Bump", p.Bump);
                m.SetFloat("_VertexAO", 0f); m.SetFloat("_EdgeWear", 0f);
                m.enableInstancing = true;
                EditorUtility.SetDirty(m);
                // Kit variant: the Windrest kit carries baked corner shading (R) and worn edges (G) in its vertex colours.
                var k = SaveMat(kv.Key + "_Kit", painterly);
                k.CopyPropertiesFromMaterial(m);
                k.SetFloat("_VertexAO", 1f); k.SetFloat("_EdgeWear", 0.8f);
                k.enableInstancing = true;
                EditorUtility.SetDirty(k);
            }
            var cloud = Shader.Find("LastSkyfarer/CloudSea");
            var sea = SaveMat("MI_CloudSea", cloud);
            sea.SetTexture("_BrushNoise", noise); sea.SetFloat("_CloudScale", 170f); sea.SetFloat("_Drift", 2f); sea.SetFloat("_Glow", 0.35f);
            var puff = SaveMat("MI_CloudPuff", cloud);
            puff.SetTexture("_BrushNoise", noise); puff.SetColor("_ShadowColor", Hex("#CFC6E6")); puff.SetColor("_LightColor", Hex("#FFFFFF"));
            puff.SetFloat("_CloudScale", 70f); puff.SetFloat("_Drift", 0.6f); puff.SetFloat("_Glow", 0.5f);
            var ribbon = SaveMat("MI_WindRibbon", Shader.Find("LastSkyfarer/WindRibbon"));
            ribbon.SetColor("_Color", Hex("#CFEFFF")); ribbon.SetFloat("_Intensity", 0.9f);
            var impossible = SaveMat("MI_WindRibbon_Impossible", Shader.Find("LastSkyfarer/WindRibbon"));
            impossible.SetColor("_Color", Hex("#4BB3FF")); impossible.SetFloat("_Intensity", 2.2f); impossible.SetFloat("_FlowSpeed", 9f);
            var sky = SaveMat("M_PaintedSky", Shader.Find("LastSkyfarer/PaintedSky"));
            sky.SetFloat("_SunSize", 0.0004f);
            sky.SetTexture("_BrushNoise", noise);
            // Villagers' stand-in figures take their speaker colour.
            foreach (var sp in StoryManager.Instance.Database.Speakers.Values)
            {
                var m = SaveMat("MI_Figure_" + sp.Id, painterly);
                var c = Hex(sp.Color);
                m.SetTexture("_BrushNoise", noise);
                m.SetColor("_ColorA", c); m.SetColor("_ColorB", c * 0.8f);
                m.SetFloat("_BrushScale", 0.8f); m.SetFloat("_StrokeMix", 0.5f); m.SetFloat("_WindAmount", 0f); m.SetFloat("_ShadeAmount", 1f);
            }
            AssetDatabase.SaveAssets();
        }

        static Material Mat(string name) => name != null && Mats.TryGetValue(name, out var m) ? m : Mats["MI_Stone"];

        // ------------------------------------------------------------ meshes for the engine shapes Unity lacks
        static Dictionary<string, Mesh> BuildMeshes()
        {
            Directory.CreateDirectory(GenDir);
            Mesh Save(string name, Mesh m)
            {
                string path = $"{GenDir}/{name}.asset";
                var old = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if (old) { old.Clear(); EditorUtility.CopySerialized(m, old); m = old; }
                else AssetDatabase.CreateAsset(m, path);
                return m;
            }
            var d = new Dictionary<string, Mesh>
            {
                ["Cylinder"] = Save("Cylinder48", Prism(48, 0.5f, 0.5f)),
                ["Cone"] = Save("Cone48", Prism(48, 0.5f, 0f)),
                ["Plane"] = Save("Plane1", PlaneMesh()),
                ["Cube"] = Resources.GetBuiltinResource<Mesh>("Cube.fbx"),
                ["Sphere"] = Resources.GetBuiltinResource<Mesh>("Sphere.fbx"),
            };
            AssetDatabase.SaveAssets();
            return d;
        }

        /// <summary>A 1 m tall shape centred on its pivot (like Unreal's basic shapes): a cylinder, or a cone when top is 0.</summary>
        static Mesh Prism(int n, float bottom, float top)
        {
            var v = new List<Vector3>(); var nr = new List<Vector3>(); var tri = new List<int>();
            float slope = (bottom - top);           // over 1 m of height
            for (int i = 0; i <= n; i++)
            {
                float a = i * Mathf.PI * 2f / n;
                var dir = new Vector3(Mathf.Cos(a), 0f, Mathf.Sin(a));
                var normal = new Vector3(dir.x, slope, dir.z).normalized;
                v.Add(dir * bottom + Vector3.down * 0.5f); nr.Add(normal);
                v.Add(dir * top + Vector3.up * 0.5f); nr.Add(normal);
            }
            for (int i = 0; i < n; i++)
            {
                int b = i * 2;
                tri.AddRange(new[] { b, b + 1, b + 2, b + 1, b + 3, b + 2 });
            }
            void Cap(float y, float r, bool up)
            {
                if (r <= 0f) return;
                int c = v.Count;
                v.Add(new Vector3(0f, y, 0f)); nr.Add(up ? Vector3.up : Vector3.down);
                for (int i = 0; i <= n; i++) { float a = i * Mathf.PI * 2f / n; v.Add(new Vector3(Mathf.Cos(a) * r, y, Mathf.Sin(a) * r)); nr.Add(up ? Vector3.up : Vector3.down); }
                for (int i = 0; i < n; i++) { if (up) tri.AddRange(new[] { c, c + 2 + i, c + 1 + i }); else tri.AddRange(new[] { c, c + 1 + i, c + 2 + i }); }
            }
            Cap(0.5f, top, true);
            Cap(-0.5f, bottom, false);
            var m = new Mesh { name = top > 0 ? "Cylinder48" : "Cone48" };
            m.SetVertices(v); m.SetNormals(nr); m.SetTriangles(tri, 0);
            m.RecalculateBounds();
            return m;
        }

        static Mesh PlaneMesh()
        {
            var m = new Mesh { name = "Plane1" };
            m.vertices = new[] { new Vector3(-0.5f, 0, -0.5f), new Vector3(-0.5f, 0, 0.5f), new Vector3(0.5f, 0, 0.5f), new Vector3(0.5f, 0, -0.5f) };
            m.normals = Enumerable.Repeat(Vector3.up, 4).ToArray();
            m.uv = new[] { Vector2.zero, Vector2.up, Vector2.one, Vector2.right };
            m.triangles = new[] { 0, 1, 2, 0, 2, 3 };
            m.RecalculateBounds();
            return m;
        }

        // ------------------------------------------------------------ the Windrest kit
        static Dictionary<string, GameObject> BuildKitPrefabs()
        {
            Directory.CreateDirectory(KitPrefabDir);
            var result = new Dictionary<string, GameObject>();
            foreach (string path in AssetDatabase.FindAssets("t:Model", new[] { KitDir }).Select(AssetDatabase.GUIDToAssetPath))
            {
                string name = Path.GetFileNameWithoutExtension(path);
                var mi = (ModelImporter)AssetImporter.GetAtPath(path);
                mi.importAnimation = false;
                mi.animationType = ModelImporterAnimationType.None;
                mi.addCollider = false;
                mi.isReadable = false;
                mi.importCameras = mi.importLights = false;
                mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
                mi.SaveAndReimport();
                // Map each material slot (named after its painterly instance) to ours.
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                var slots = model.GetComponentsInChildren<Renderer>().SelectMany(r => r.sharedMaterials).Where(m => m).Select(m => m.name).Distinct().ToList();
                bool changed = false;
                foreach (string seen in slots)
                {
                    // After a first run the slots show our material names; map back to the FBX's own slot name.
                    string slot = seen.EndsWith("_Kit") ? seen.Substring(0, seen.Length - 4) : seen;
                    if (slot == "MI_LanternGlow") slot = "MI_Brass";
                    string wanted = (name == "SM_LanternPost" || name == "SM_HangingLantern") && slot == "MI_Brass" ? "MI_LanternGlow" : slot;
                    if (!Mats.ContainsKey(wanted)) { Debug.LogWarning($"LS_KIT {name}: no material for slot {slot}"); continue; }
                    mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), slot), Mats.TryGetValue(wanted + "_Kit", out var kitMat) ? kitMat : Mats[wanted]);
                    changed = true;
                }
                if (changed) mi.SaveAndReimport();
                model = AssetDatabase.LoadAssetAtPath<GameObject>(path);

                // Prefab: a root in Unreal's axes (the Blender export arrives turned 90 degrees in Unity).
                var root = new GameObject(name);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(model);
                inst.transform.SetParent(root.transform, false);
                inst.transform.localRotation = Quaternion.Euler(0f, -90f, 0f) * inst.transform.localRotation;   // keep the FBX's own Z-up turn
                string prefabPath = $"{KitPrefabDir}/{name}.prefab";
                result[name] = PrefabUtility.SaveAsPrefabAsset(root, prefabPath);
                Object.DestroyImmediate(root);
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"LS_BRINDLE kit prefabs {result.Count}");
            return result;
        }

        // ------------------------------------------------------------ the scene
        static void BuildScene(Dictionary<string, Mesh> meshes, Dictionary<string, GameObject> kit)
        {
            var layout = JsonUtility.FromJson<Layout>(File.ReadAllText(LayoutPath));
            Directory.CreateDirectory("Assets/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var groups = new Dictionary<string, Transform>();
            Transform Group(string folder)
            {
                folder = string.IsNullOrEmpty(folder) ? "Misc" : folder;
                if (groups.TryGetValue(folder, out var t)) return t;
                Transform parent = null;
                int slash = folder.LastIndexOf('/');
                if (slash > 0) parent = Group(folder.Substring(0, slash));
                t = new GameObject(slash > 0 ? folder.Substring(slash + 1) : folder).transform;
                t.SetParent(parent, false);
                groups[folder] = t;
                return t;
            }
            int CullLayer(float metres)
            {
                if (metres <= 0f) return 0;
                for (int i = 0; i < CullDistances.Length; i++) if (metres <= CullDistances[i] + 1f) return BrindleLevel.FirstCullLayer + i;
                return 0;
            }

            Transform playerStart = null;
            var lamps = new List<Light>();
            int shapes = 0, kits = 0;
            var byName = new Dictionary<string, GameObject>();
            var placed = new List<(GameObject go, Item it)>();
            foreach (var it in layout.Items)
            {
                Vector3 pos = it.Pos.ToV(), scale = it.Scale.ToV();
                var rot = Quaternion.Euler(it.Euler.ToV());
                switch (it.Kind)
                {
                    case "shape":
                    {
                        if (!meshes.TryGetValue(it.Mesh, out var mesh)) { Debug.LogWarning("LS_BRINDLE unknown shape " + it.Mesh); continue; }
                        var go = new GameObject(it.Name);
                        go.transform.SetParent(Group(it.Folder), false);
                        go.transform.SetPositionAndRotation(pos, rot);
                        go.transform.localScale = scale;
                        if (!it.Hidden)
                        {
                            go.AddComponent<MeshFilter>().sharedMesh = mesh;
                            var mr = go.AddComponent<MeshRenderer>();
                            mr.sharedMaterial = Mat(it.Material);
                            bool cloud = it.Material == "MI_CloudSea" || it.Material == "MI_CloudPuff";
                            mr.shadowCastingMode = cloud ? ShadowCastingMode.Off : ShadowCastingMode.On;
                            mr.receiveShadows = !cloud;
                        }
                        if (it.Collider)
                        {
                            if (it.Mesh == "Cube") go.AddComponent<BoxCollider>();
                            else if (it.Mesh == "Sphere") go.AddComponent<SphereCollider>();
                            else if (it.Mesh != "Plane") go.AddComponent<MeshCollider>().sharedMesh = mesh;
                        }
                        if (it.Climbable) go.AddComponent<Climbable>();
                        GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic);
                        byName[it.Name] = go;
                        placed.Add((go, it));
                        shapes++;
                        break;
                    }
                    case "kit":
                    {
                        if (!kit.TryGetValue(it.Mesh, out var prefab)) { Debug.LogWarning("LS_BRINDLE unknown kit piece " + it.Mesh); continue; }
                        var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                        go.name = it.Name;
                        go.transform.SetParent(Group(it.Folder), false);
                        go.transform.SetPositionAndRotation(pos, rot);
                        go.transform.localScale = scale;
                        int layer = CullLayer(it.Cull);
                        foreach (var t in go.GetComponentsInChildren<Transform>(true)) t.gameObject.layer = layer;
                        foreach (var r in go.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = it.Shadow ? ShadowCastingMode.On : ShadowCastingMode.Off;
                        if (it.Spin != 0f) go.AddComponent<Spinner>().DegreesPerSecond = -it.Spin;
                        else foreach (var t in go.GetComponentsInChildren<Transform>(true)) GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic);
                        placed.Add((go, it));
                        kits++;
                        break;
                    }
                    case "wind":
                    {
                        var go = new GameObject(it.Name);
                        go.transform.SetParent(Group("Wind"), false);
                        go.transform.position = it.Points.Count > 0 ? it.Points[0].ToV() : pos;
                        var w = go.AddComponent<WindVolume>();
                        w.Type = (WindType)Enum.Parse(typeof(WindType), it.WindType, true);
                        w.Points = it.Points.Select(p => p.ToV()).ToList();
                        w.Radius = it.Radius; w.Strength = it.Strength; w.StartsHidden = it.StartsHidden;
                        w.ImpossibleRoute = it.Tags.Contains("impossible_route");
                        w.RevealFlag = it.Tags.Contains("revealed_wind_1") ? BrindleStoryDirector.RevealedWindFlag : "";
                        var ribbons = go.AddComponent<WindRibbons>();
                        ribbons.Material = w.ImpossibleRoute ? Mats["MI_WindRibbon_Impossible"] : Mats["MI_WindRibbon"];
                        ribbons.Width = Mathf.Clamp(it.Radius * 0.08f, 0.5f, 1.2f);
                        break;
                    }
                    case "lamp":
                    {
                        var go = new GameObject(it.Name);
                        go.transform.SetParent(Group(it.Folder), false);
                        go.transform.position = pos;
                        var l = go.AddComponent<Light>();
                        l.type = LightType.Point; l.color = new Color(1f, 0.68f, 0.38f); l.intensity = 2.2f;
                        l.range = it.Name.Contains("Desk") ? 6f : 12f;
                        l.shadows = LightShadows.None;
                        lamps.Add(l);
                        break;
                    }
                    case "start":
                    {
                        playerStart = new GameObject(it.Name).transform;
                        playerStart.SetPositionAndRotation(pos, rot);
                        break;
                    }
                    default:
                        if (it.Kind.StartsWith("marker_"))
                        {
                            var go = new GameObject(it.Name);
                            go.transform.SetParent(Group("Story/Markers"), false);
                            go.transform.position = pos;
                            var m = go.AddComponent<MapMarker>();
                            m.Kind = it.Kind.Substring(7); m.LocationId = it.Id; m.Quest = it.Quest; m.Objective = it.Objective;
                        }
                        break;
                }
            }

            // Story state on world pieces (windrest.gd / ALSBrindleStory::ApplyStoryState).
            if (byName.TryGetValue("Bluff_EdgeWall", out var edge)) Conditional(edge, false, true, "!piko_joined");
            foreach (var kv in byName.Where(k => k.Key.StartsWith("Compartment_"))) Conditional(kv.Value, true, false, "compartment_open");

            // Polish pass 1: dressing that makes the village square feel lived in (our new Windrest props).
            foreach (var (mesh, x, z, yaw, sx, sy, sz, y) in SquareDressing)
            {
                if (!kit.TryGetValue(mesh, out var prefab)) { Debug.LogWarning("LS_BRINDLE no prop " + mesh); continue; }
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                go.name = "Dress_" + mesh.Substring(3);
                go.transform.SetParent(Group("Art/Dressing"), false);
                go.transform.SetPositionAndRotation(new Vector3(x, y, z), Quaternion.Euler(0f, yaw, 0f));
                go.transform.localScale = new Vector3(sx, sy, sz);
                int layer = BrindleLevel.FirstCullLayer + (mesh == "SM_PottedPlant" || mesh == "SM_FlowerBox" ? 1 : 2);
                foreach (var t in go.GetComponentsInChildren<Transform>(true)) { t.gameObject.layer = layer; GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic); }
                placed.Add((go, new Item { Name = go.name }));
            }
            BuildStoryPlacements(Group("Story"), meshes);
            var ground = BuildGround(Group("Island"), placed, byName, kit);

            // Light, sky and the level.
            var sunGo = new GameObject("Sun");
            var sun = sunGo.AddComponent<Light>();
            sun.type = LightType.Directional; sun.shadows = LightShadows.Soft; sun.shadowStrength = 0.75f;
            sun.shadowBias = 0.05f; sun.shadowNormalBias = 0.4f;
            var tod = new GameObject("TimeOfDay").AddComponent<TimeOfDayDirector>();
            tod.Sun = sun;
            tod.Sky = Mats["M_PaintedSky"];
            tod.LampMaterials = new[] { Mats["MI_LanternGlow"], Mats["MI_LanternGlow_Kit"] };
            // Night: the square's lanterns throw warm pools of light (six small point lights, off by day).
            var nightLights = new List<Light>();
            foreach (var t in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None).Where(t => t.name.StartsWith("Square_Lantern_") && t.parent && t.parent.name == "Windrest"))
            {
                var l = new GameObject("NightLight").AddComponent<Light>();
                l.transform.SetParent(t, false);
                l.transform.position = t.position + Vector3.up * 2.45f - t.right * 0.0f;
                l.type = LightType.Point; l.color = new Color(1f, 0.7f, 0.42f); l.range = 11f; l.intensity = 2.5f; l.shadows = LightShadows.None;
                l.enabled = false;
                nightLights.Add(l);
            }
            tod.NightLights = nightLights.ToArray();
            Debug.Log($"LS_BRINDLE night lights {nightLights.Count}");
            // Post-processing: tonemapping, a painterly grade that follows the time of day, soft bloom, vignette.
            var post = new GameObject("PostProcessing").AddComponent<Volume>();
            post.isGlobal = true;
            post.sharedProfile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(RenderingSetup.PostProfile);
            tod.Grade = post.sharedProfile;
            RenderSettings.skybox = Mats["M_PaintedSky"];
            RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.fog = true;
            var lighting = new LightingSettings { name = "BrindleLighting", bakedGI = false, realtimeGI = false };
            AssetDatabase.DeleteAsset("Assets/Scenes/BrindleLighting.lighting");
            AssetDatabase.CreateAsset(lighting, "Assets/Scenes/BrindleLighting.lighting");
            Lightmapping.lightingSettings = lighting;

            Transform Spawn(string name, Vector3 p, float yaw)
            {
                var t = new GameObject(name).transform;
                t.SetParent(Group("Story/Spawns"), false);
                t.SetPositionAndRotation(p, Quaternion.Euler(0f, yaw, 0f));
                return t;
            }
            var level = new GameObject("BrindleLevel").AddComponent<BrindleLevel>();
            level.KieranPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Kieran.prefab");
            level.PlayerStart = playerStart;
            if (playerStart) playerStart.SetParent(Group("Story/Spawns"), true);
            level.InteriorSpawn = Spawn("Spawn_WorkshopInterior", new Vector3(-3000f, 1.0f, -5.5f), 0f);
            level.DoorSpawn = Spawn("Spawn_WorkshopDoor", new Vector3(590.5f, 21.2f, 75f), -90f);
            level.TimeOfDay = tod;
            level.LayerCullDistances = CullDistances;
            tod.Apply("Morning", true);

            EditorSceneManager.SaveScene(scene, ScenePath);
            var list = EditorBuildSettings.scenes.Where(s => s.path != ScenePath).ToList();
            list.Insert(0, new EditorBuildSettingsScene(ScenePath, true));
            EditorBuildSettings.scenes = list.ToArray();
            Debug.Log($"LS_BRINDLE scene {ScenePath}: {shapes} shapes, {kits} kit pieces, {layout.Items.Count(i => i.Kind == "wind")} wind lines, start {(playerStart ? playerStart.position.ToString() : "missing")}");
        }

        // Square dressing: prop, x, z (Unity metres, square at the origin), yaw, scale x/y/z, height.
        static readonly (string, float, float, float, float, float, float, float)[] SquareDressing =
        {
            ("SM_Barrel", -13.2f, 17.0f, 10f, 1, 1, 1, 0), ("SM_Barrel", -12.4f, 17.7f, 40f, 1, 1, 1, 0), ("SM_Barrel", -12.8f, 17.3f, 0f, 1, 1, 1, 0.9f),
            ("SM_Barrel", 13.4f, 16.8f, 70f, 1, 1, 1, 0), ("SM_Barrel", -13.6f, -17.4f, 15f, 1, 1, 1, 0), ("SM_Barrel", -12.9f, -18.2f, 75f, 1, 1, 1, 0),
            ("SM_Sacks", 7.6f, 17.2f, 20f, 1, 1, 1, 0), ("SM_Sacks", -7.8f, -17.6f, 200f, 1, 1, 1, 0), ("SM_Sacks", 13.6f, -16.6f, 110f, 1, 1, 1, 0),
            ("SM_Cart", -19.5f, 5.5f, 100f, 1, 1, 1, 0), ("SM_HayBale", -21.2f, 2.4f, 12f, 1, 1, 1, 0), ("SM_HayBale", -21.0f, 2.6f, 5f, 1, 1, 1, 0.5f),
            ("SM_Firewood", -21.8f, -5.5f, 90f, 1, 1, 1, 0), ("SM_Well", 12.0f, -20.0f, 25f, 1, 1, 1, 0), ("SM_Trough", 15.4f, -17.2f, 120f, 1, 1, 1, 0),
            ("SM_PottedPlant", 7.2f, 0.6f, 0f, 1, 1, 1, 0), ("SM_PottedPlant", 0.4f, 7.2f, 60f, 1, 1, 1, 0), ("SM_PottedPlant", -0.4f, -7.2f, 120f, 1, 1, 1, 0),
            ("SM_PottedPlant", 9.6f, 15.8f, 0f, 0.8f, 0.8f, 0.8f, 0), ("SM_PottedPlant", -9.8f, -15.6f, 0f, 0.8f, 0.8f, 0.8f, 0),
            ("SM_Bunting", 0f, 14.0f, 90f, 1, 1, 2.0f, 0.9f), ("SM_Bunting", 0f, -14.0f, 90f, 1, 1, 2.0f, 0.9f), ("SM_Bunting", 0f, 0f, 0f, 1, 1, 2.6f, 2.2f),
            ("SM_LaundryLine", -31f, 17f, 20f, 1, 1, 1, 0),
            ("SM_Bush", 25.5f, 6.5f, 0f, 1.2f, 1.2f, 1.2f, 0), ("SM_Bush", 19.5f, 17.5f, 50f, 1, 1, 1, 0), ("SM_Bush", -6.5f, 25.5f, 100f, 1.3f, 1.1f, 1.3f, 0),
            ("SM_Bush", -25.0f, -9.0f, 160f, 1.1f, 1.1f, 1.1f, 0), ("SM_Bush", 6.0f, -25.5f, 220f, 1.2f, 1.0f, 1.2f, 0), ("SM_Bush", -18.0f, -19.0f, 280f, 1, 1, 1, 0),
            // Whispermill: a working farm round the first windmill.
            ("SM_HayBale", -271f, 292f, 20f, 1, 1, 1, 0), ("SM_HayBale", -270.5f, 293.5f, 35f, 1, 1, 1, 0), ("SM_HayBale", -271f, 292.6f, 25f, 1, 1, 1, 0.5f),
            ("SM_Sacks", -289f, 307f, 140f, 1, 1, 1, 0), ("SM_Cart", -262f, 314f, 30f, 1, 1, 1, 0), ("SM_Barrel", -276f, 309f, 0f, 1, 1, 1, 0),
            ("SM_Barrel", -275.2f, 309.8f, 40f, 1, 1, 1, 0), ("SM_Trough", -292f, 296f, 70f, 1, 1, 1, 0), ("SM_Sacks", -378f, 362f, 60f, 1, 1, 1, 0),
            ("SM_HayBale", -396f, 258f, 80f, 1, 1, 1, 0), ("SM_Bush", -238f, 300f, 0f, 1.3f, 1.2f, 1.3f, 0), ("SM_Bush", -236f, 340f, 90f, 1.1f, 1.1f, 1.1f, 0),
            // Old Cartographer's Bluff: Elias's workshop, lived-in but left alone.
            ("SM_Barrel", 591.0f, 70.0f, 0f, 1, 1, 1, 20f), ("SM_Barrel", 591.8f, 69.0f, 30f, 1, 1, 1, 20f), ("SM_Firewood", 594f, 88.5f, 0f, 1, 1, 1, 20f),
            ("SM_PottedPlant", 590.4f, 78.6f, 0f, 1, 1, 1, 20f), ("SM_PottedPlant", 590.4f, 71.4f, 90f, 0.9f, 0.9f, 0.9f, 20f), ("SM_Bush", 562f, 42f, 0f, 1.3f, 1.2f, 1.3f, 20f),
            ("SM_Bush", 622f, 30f, 120f, 1.2f, 1.1f, 1.2f, 20f), ("SM_Bush", 652f, 104f, 200f, 1.1f, 1.1f, 1.1f, 20f), ("SM_Sacks", 633f, 122f, 40f, 1, 1, 1, 20f),
            ("SM_Bush", 548f, 120f, 60f, 1.3f, 1.2f, 1.3f, 20f),
            // Skywatch Point: Tessa's lookout.
            ("SM_PottedPlant", 34f, 472f, 0f, 1, 1, 1, 25.6f), ("SM_PottedPlant", 46.5f, 471.5f, 50f, 1, 1, 1, 25.6f), ("SM_Barrel", 32f, 486f, 0f, 1, 1, 1, 25.6f),
            ("SM_Sacks", 33.5f, 488f, 30f, 0.8f, 0.8f, 0.8f, 25.6f), ("SM_Bunting", 40f, 489.5f, 90f, 1, 0.6f, 2.0f, 23.9f),
            // Cloud Edge: the flower terrace over the cloud sea.
            ("SM_PottedPlant", -108f, 548f, 0f, 1, 1, 1, 1f), ("SM_PottedPlant", -92f, 548f, 70f, 1, 1, 1, 1f), ("SM_Bunting", -100f, 557f, 90f, 1, 0.6f, 2.5f, -0.4f),
            ("SM_Barrel", -127f, 530f, 0f, 1, 1, 1, 1f),
            // Orchard Vale: harvest time.
            ("SM_Cart", -352f, 26f, 95f, 1, 1, 1, 0), ("SM_HayBale", -356f, 33f, 10f, 1, 1, 1, 0), ("SM_Sacks", -346f, 19f, 200f, 1, 1, 1, 0),
            ("SM_Barrel", -362f, 36f, 0f, 1, 1, 1, 0), ("SM_Barrel", -362.8f, 36.9f, 50f, 1, 1, 1, 0), ("SM_Trough", -414f, 34f, 20f, 1, 1, 1, 0),
            ("SM_Bush", -342f, -40f, 0f, 1.3f, 1.2f, 1.3f, 0), ("SM_Bush", -470f, 40f, 90f, 1.2f, 1.1f, 1.2f, 0),
            // Upper Cliffs, where the game opens.
            ("SM_Bush", 300f, 340f, 0f, 1.2f, 1.1f, 1.2f, 15f), ("SM_Bush", 352f, 312f, 140f, 1.1f, 1.0f, 1.1f, 15f), ("SM_Bush", 278f, 296f, 220f, 1.3f, 1.2f, 1.3f, 15f),
        };

        // ------------------------------------------------------------ the ground (polish pass 1)
        static readonly string[] SnapKeys = { "Orchard_", "_Trunk", "_Canopy", "Tree", "Rock_", "RimRock", "Grass_", "Wheat_", "Petals", "Fence", "Beehive", "Orchard_Crate", "Ladder" };
        static readonly string[] SkipKeys = { "Island_", "CloudPuff", "CloudSea", "MistIsland", "Sky", "FloatingIsle", "Workshop_", "Compartment_", "Square_Paving", "Bluff_EdgeWall" };

        static IslandGround BuildGround(Transform parent, List<(GameObject go, Item it)> placed, Dictionary<string, GameObject> byName, Dictionary<string, GameObject> kit)
        {
            var input = new IslandTerrainBuilder.Input();
            foreach (var (go, it) in placed)
            {
                string n = it.Name;
                if (SkipKeys.Any(n.Contains)) continue;
                if (SnapKeys.Any(n.Contains)) { if (go.transform.position.y < 2f) input.Snap.Add(go.transform); continue; }
                if (n.StartsWith("Path_") && !n.Contains("_Art"))
                {
                    var size = new Vector2(go.transform.localScale.x, go.transform.localScale.z);
                    input.Flat.Add(IslandTerrainBuilder.Zone.FromTransform(go.transform, size, 5f));
                    bool village = n.Contains("PostHouse") || n.Contains("Tavern") || n.Contains("Homes");
                    (village ? input.Cobble : input.Dirt).Add(IslandTerrainBuilder.Zone.FromTransform(go.transform, size * 0.9f, village ? 2f : 3.5f));
                    if (village) input.Dirt.Add(IslandTerrainBuilder.Zone.FromTransform(go.transform, size, 3.5f));
                    continue;
                }
                var rs = go.GetComponentsInChildren<Renderer>();
                var cs = go.GetComponentsInChildren<Collider>();
                if (rs.Length == 0 && cs.Length == 0) continue;
                Bounds b = rs.Length > 0 ? rs[0].bounds : cs[0].bounds;
                foreach (var r in rs) b.Encapsulate(r.bounds);
                foreach (var c in cs) b.Encapsulate(c.bounds);
                if (b.min.y > 1.5f || b.max.y < -2f || b.size.x > 300f) continue;
                bool building = n.StartsWith("Home_") || n.StartsWith("PostHouse") || n.StartsWith("WindsongTavern") || n.StartsWith("EliasWorkshop") || n.Contains("Windmill");
                input.Flat.Add(IslandTerrainBuilder.Zone.FromBounds(b, building ? 9f : 5f));
                if (building) input.Dirt.Add(IslandTerrainBuilder.Zone.FromBounds(b, 3f));
            }
            // The village square: cobbles with a worn, ragged edge; story places stay level.
            input.Flat.Add(new IslandTerrainBuilder.Zone { Round = true, Half = new Vector2(24f, 24f), Margin = 8f });
            input.Cobble.Add(new IslandTerrainBuilder.Zone { Round = true, Half = new Vector2(19f, 19f), Margin = 4f });
            input.Dirt.Add(new IslandTerrainBuilder.Zone { Round = true, Half = new Vector2(21f, 21f), Margin = 5f });
            foreach (var d in NarrativeDatabase.LoadFromResources().Level.Interactables)
                input.Flat.Add(new IslandTerrainBuilder.Zone { Round = true, Centre = new Vector2(d.Position.x, d.Position.z), Half = new Vector2(2f, 2f), Margin = 4f });
            if (byName.TryGetValue("Square_Paving", out var paving) && paving.TryGetComponent<MeshRenderer>(out var pr)) pr.enabled = false;   // painted cobbles now
            if (byName.TryGetValue("Island_Top", out var top))
            {
                top.transform.position += Vector3.down * 0.05f;                                                        // the ground mesh covers it
                if (top.TryGetComponent<MeshRenderer>(out var tr)) tr.enabled = false;                                 // the new cliffs show instead
            }
            if (byName.TryGetValue("Island_Underside", out var under) && under.TryGetComponent<MeshRenderer>(out var ur)) ur.enabled = false;
            IslandTerrainBuilder.BuildUnderside(parent, Mats["MI_CliffRock_Kit"]);

            var grassMesh = SaveMesh("GrassClump", IslandTerrainBuilder.GrassClump(false));
            var flowerMesh = SaveMesh("Wildflowers", IslandTerrainBuilder.GrassClump(true));
            var groundMat = SaveMat("M_Ground", Shader.Find("LastSkyfarer/PainterlyGround"));
            groundMat.SetTexture("_BrushNoise", noise);
            var grassMat = SaveMat("M_Grass", Shader.Find("LastSkyfarer/PainterlyGrass"));
            grassMat.SetTexture("_BrushNoise", noise); grassMat.enableInstancing = true;
            var flowerMat = SaveMat("M_Wildflowers", Shader.Find("LastSkyfarer/PainterlyGrass"));
            flowerMat.SetTexture("_BrushNoise", noise); flowerMat.enableInstancing = true;
            var ig = IslandTerrainBuilder.Build(parent, input, groundMat, grassMesh, flowerMesh, grassMat, flowerMat);

            // The Whispermill wheat: dense instanced stalks over the field (the old wheat cards go).
            var wheatMat = SaveMat("M_Wheat", Shader.Find("LastSkyfarer/PainterlyGrass"));
            wheatMat.SetTexture("_BrushNoise", noise); wheatMat.enableInstancing = true;
            wheatMat.SetColor("_Root", Hex("#8C6A2A")); wheatMat.SetColor("_TipA", Hex("#F0D27A")); wheatMat.SetColor("_TipB", Hex("#D8A84A"));
            wheatMat.SetFloat("_Wind", 0.18f); wheatMat.SetFloat("_WindSpeed", 1.5f);
            ig.WheatMesh = SaveMesh("WheatClump", IslandTerrainBuilder.WheatClump());
            ig.WheatMaterial = wheatMat;
            if (byName.TryGetValue("Whispermill_Wheat", out var field))
            {
                var fb = field.GetComponent<Collider>().bounds;
                ig.WheatFields.Add(new Rect(fb.min.x + 2f, fb.min.z + 2f, fb.size.x - 4f, fb.size.z - 4f));
            }
            foreach (var kv in byName.Where(k => k.Key.EndsWith("_Tower") && k.Key.StartsWith("Windmill_")))
                ig.WheatHoles.Add(new Vector3(kv.Value.transform.position.x, kv.Value.transform.position.z, 8f));
            foreach (var (go, it) in placed.Where(p => p.it.Name.StartsWith("Mill_") || p.it.Name.StartsWith("Dress_")))
                ig.WheatHoles.Add(new Vector3(go.transform.position.x, go.transform.position.z, 3.5f));
            // The old grass and wheat cards are replaced by the instanced meadow and field.
            foreach (var (go, it) in placed.Where(p => p.it.Mesh == "SM_GrassPatch" || p.it.Mesh == "SM_WheatPatch"))
                foreach (var r in go.GetComponentsInChildren<Renderer>()) r.enabled = false;
            // Rocky plateaus in place of the smooth slabs (Skywatch hill, the Upper Cliffs, the Bluff).
            int seed = 1;
            foreach (var (go, it) in placed.Where(p => p.it.Mesh == "SM_Plateau" && p.it.Scale != null && p.it.Scale.y > 5f).ToList())
            {
                foreach (var r in go.GetComponentsInChildren<Renderer>()) r.enabled = false;
                IslandTerrainBuilder.BuildPlateau(parent, "Rocky_" + it.Name.Replace("_Art", ""), it.Pos.ToV(), it.Scale.ToV(), Mats["MI_CliffRock_Kit"], groundMat, seed++);
                var sz = it.Scale.ToV();
                ig.Plateaus.Add(new Vector4(it.Pos.x, it.Pos.z, sz.x * 0.5f, sz.z * 0.5f));
                ig.PlateauHeights.Add(it.Pos.y + sz.y);
                PlateauRocks(parent, kit, it.Pos.ToV(), sz, seed * 17);
            }
            // Grass grows on the low terraces too (Cloud Edge, the Upper Cliffs lookout); their kit tops stay.
            foreach (var (go, it) in placed.Where(p => p.it.Mesh == "SM_Plateau" && p.it.Scale != null && p.it.Scale.y <= 5f))
            {
                var sz = it.Scale.ToV();
                ig.Plateaus.Add(new Vector4(it.Pos.x, it.Pos.z, sz.x * 0.5f, sz.z * 0.5f));
                ig.PlateauHeights.Add(it.Pos.y + sz.y);
            }
            // Cloud puffs sit lower and smaller, so the cliffs of the island show above them.
            foreach (var kv in byName.Where(k => k.Key.StartsWith("CloudPuff_")))
            {
                kv.Value.transform.position += Vector3.down * 55f;
                kv.Value.transform.localScale *= 0.65f;
            }
            return ig;
        }

        /// <summary>Hand-placed-looking breakup round a rocky plateau (pass 3): boulders leaning against its foot,
        /// half buried, and a few smaller stones on the rim. Visual only, like the rest of the kit.</summary>
        static void PlateauRocks(Transform parent, Dictionary<string, GameObject> kit, Vector3 c, Vector3 size, int seed)
        {
            var rnd = new System.Random(seed);
            float hx = size.x * 0.5f, hz = size.z * 0.5f, h = size.y;
            Vector3 Edge(float a, float k)
            {
                float ca = Mathf.Cos(a), sa = Mathf.Sin(a);
                return new Vector3(c.x + Mathf.Sign(ca) * Mathf.Pow(Mathf.Abs(ca), 0.5f) * hx * k, 0f, c.z + Mathf.Sign(sa) * Mathf.Pow(Mathf.Abs(sa), 0.5f) * hz * k);
            }
            var group = new GameObject("PlateauRocks").transform;
            group.SetParent(parent, false);
            int n = Mathf.RoundToInt((size.x + size.z) / 7f);
            for (int i = 0; i < n; i++)
            {
                bool rim = rnd.NextDouble() < 0.25;
                float a = (float)(i + rnd.NextDouble() * 0.6) / n * Mathf.PI * 2f;
                var p = Edge(a, rim ? 0.9f : 1.06f + (float)rnd.NextDouble() * 0.06f);
                p.y = rim ? c.y + h - 0.4f : c.y - 0.8f + (float)rnd.NextDouble() * h * 0.25f;
                float s = rim ? 1.0f + (float)rnd.NextDouble() * 1.2f : 2.2f + (float)rnd.NextDouble() * 3.5f;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(kit["SM_Rock_" + rnd.Next(3)]);
                go.transform.SetParent(group, false);
                go.transform.SetPositionAndRotation(p, Quaternion.Euler((float)rnd.NextDouble() * 20f - 10f, (float)rnd.NextDouble() * 360f, (float)rnd.NextDouble() * 20f - 10f));
                go.transform.localScale = new Vector3(s, s * (0.7f + (float)rnd.NextDouble() * 0.6f), s);
                foreach (var t in go.GetComponentsInChildren<Transform>(true)) { t.gameObject.layer = BrindleLevel.FirstCullLayer + 3; GameObjectUtility.SetStaticEditorFlags(t.gameObject, StaticEditorFlags.BatchingStatic); }
            }
        }

        static Mesh SaveMesh(string name, Mesh m)
        {
            string path = $"{GenDir}/{name}.asset";
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        static void Conditional(GameObject go, bool renderers, bool colliders, params string[] showIf)
        {
            var c = go.AddComponent<ConditionalObject>();
            c.ShowIf = showIf.ToList(); c.AffectRenderers = renderers; c.AffectColliders = colliders;
        }

        // ------------------------------------------------------------ villagers, things to inspect, notes, triggers, places
        static void BuildStoryPlacements(Transform root, Dictionary<string, Mesh> meshes)
        {
            var db = NarrativeDatabase.LoadFromResources();
            var visibleInspect = new HashSet<string> { "Inspect_Maps", "Inspect_Notes", "Inspect_Floorboard", "Inspect_Glider", "Inspect_WorkshopDoor", "Inspect_WorkshopDoor_Inside" };
            foreach (var d in db.Level.Interactables)
            {
                var go = new GameObject(d.Id);
                go.transform.SetParent(root, false);
                go.transform.SetPositionAndRotation(d.Position, Quaternion.Euler(0f, d.Yaw, 0f));
                var it = go.AddComponent<Interactable>();
                it.InteractableId = d.Id;
                var villager = d.Kind == "npc" ? VillagerSetup.Cast.FirstOrDefault(c => c.speaker == d.Speaker) : default;
                var villagerPrefab = villager.name != null ? AssetDatabase.LoadAssetAtPath<GameObject>($"{VillagerSetup.PrefabDir}/{villager.name}.prefab") : null;
                if (villagerPrefab)
                {
                    // A modelled villager (polish pass 1).
                    var v = (GameObject)PrefabUtility.InstantiatePrefab(villagerPrefab);
                    v.transform.SetParent(go.transform, false);
                    var cap = go.AddComponent<CapsuleCollider>(); cap.center = new Vector3(0f, 0.9f, 0f); cap.height = 1.8f; cap.radius = 0.35f;
                    it.FaceKieran = v.transform;
                }
                else if (d.Kind == "npc")
                {
                    // Stand-in villager until the character art arrives: a painted body and head in the speaker's colour.
                    var body = new GameObject("Figure");
                    body.transform.SetParent(go.transform, false);
                    var mat = Mats.TryGetValue("MI_Figure_" + d.Speaker, out var fm) ? fm : Mats["MI_Plaster"];
                    Part(body.transform, meshes["Cylinder"], mat, new Vector3(0f, 0.75f, 0f), new Vector3(0.55f, 1.5f, 0.45f));
                    Part(body.transform, meshes["Sphere"], Mats["MI_Plaster"], new Vector3(0f, 1.68f, 0f), new Vector3(0.36f, 0.4f, 0.36f));
                    var cap = go.AddComponent<CapsuleCollider>(); cap.center = new Vector3(0f, 0.9f, 0f); cap.height = 1.8f; cap.radius = 0.35f;
                    it.FaceKieran = body.transform;
                }
                else if (d.Kind == "note")
                {
                    var page = new GameObject("Page");
                    page.transform.SetParent(go.transform, false);
                    page.transform.localPosition = new Vector3(0f, 0.6f, 0f);
                    Part(page.transform, meshes["Cube"], Mats["MI_NotePaper"], Vector3.zero, new Vector3(0.36f, 0.02f, 0.46f)).transform.localRotation = Quaternion.Euler(-60f, 0f, 0f);
                    page.AddComponent<NoteBob>();
                    Conditional(go, true, false, "!collected_" + d.JournalId);
                }
                else if (visibleInspect.Contains(d.Id))
                {
                    string mat = d.Id.Contains("Door") ? "MI_Wood" : d.Id == "Inspect_Floorboard" ? "MI_WoodFloor" : "MI_Sailcloth";
                    var shape = Part(go.transform, meshes["Cube"], Mats[mat], Vector3.zero, d.Size);
                    if (d.Id == "Inspect_Glider")
                    {
                        shape.AddComponent<BoxCollider>();
                        Conditional(go, true, true, "compass_active", "!piko_joined");
                    }
                }
            }
            foreach (var t in db.Level.Triggers)
            {
                var go = new GameObject(t.Id) { layer = 2 };
                go.transform.SetParent(root, false);
                go.transform.position = t.Position;
                var box = go.AddComponent<BoxCollider>(); box.isTrigger = true; box.size = t.Size;
                go.AddComponent<StoryTriggerVolume>().TriggerId = t.Id;
            }
            foreach (var a in db.Level.Areas)
            {
                var go = new GameObject("Area_" + a.Id) { layer = 2 };
                go.transform.SetParent(root, false);
                go.transform.position = a.Position;
                var box = go.AddComponent<BoxCollider>(); box.isTrigger = true; box.size = a.Size;
                go.AddComponent<LocationArea>().LocationId = a.Id;
            }
        }

        static GameObject Part(Transform parent, Mesh mesh, Material mat, Vector3 at, Vector3 size)
        {
            var go = new GameObject(mesh.name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = at;
            go.transform.localScale = size;
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            go.AddComponent<MeshRenderer>().sharedMaterial = mat;
            return go;
        }

        // ------------------------------------------------------------ the player build
        [MenuItem("Last Skyfarer/Build Brindle Isle")]
        public static void BuildPlayer()
        {
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = "../Builds/Brindle/LastSkyfarer.exe",
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            });
            Debug.Log($"LS_BUILD brindle {report.summary.result}, {report.summary.totalSize / (1024 * 1024)} MB, {report.summary.totalErrors} errors");
        }
    }
}

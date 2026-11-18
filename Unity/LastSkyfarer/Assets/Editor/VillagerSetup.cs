// The Last Skyfarer: villagers built with the Kieran pipeline (Unity/Tools/blender/villagers). Imports each one as a
// Humanoid, gives them the stylised character shader and an idle that breathes (Mixamo idle through Humanoid), and
// saves Assets/Prefabs/Villagers/<Name>.prefab, which the Brindle builder puts in place of the stand-in figure.
//   Unity.exe -batchmode -projectPath <project> -executeMethod LastSkyfarer.EditorTools.VillagerSetup.Run -quit
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace LastSkyfarer.EditorTools
{
    public static class VillagerSetup
    {
        public const string PrefabDir = "Assets/Prefabs/Villagers";
        const string ControllerPath = "Assets/Art/Characters/Villagers/Villager.controller";
        const string IdlePath = "Assets/Art/Characters/Kieran/Animations/Mixamo_Idle.fbx";
        // speaker id (Speakers.json) -> villager name (folder Assets/Art/Characters/<Name>, model <Export>_GameReady.fbx)
        public static readonly (string speaker, string name, string export)[] Cast = { ("tavern", "Bram", "Bram_Holloway"), ("tessa", "Tessa", "Tessa_Reed"), ("villager", "Elara", "Elara_Greenborough"),
                                                                                    ("maren", "Maren", "Maren_Holt"), ("rowan", "Rowan", "Rowan_Finch") };

        public static void Run()
        {
            Directory.CreateDirectory(PrefabDir);
            Directory.CreateDirectory(Path.GetDirectoryName(ControllerPath));
            var idle = CalmIdle(AssetDatabase.LoadAllAssetsAtPath(IdlePath).OfType<AnimationClip>().First(a => !a.name.StartsWith("__preview")));
            AssetDatabase.DeleteAsset(ControllerPath);
            var ac = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            var st = ac.layers[0].stateMachine.AddState("Idle");
            st.motion = idle;
            ac.layers[0].stateMachine.defaultState = st;
            foreach (var (speaker, name, export) in Cast) Build(name, export, ac);
            AssetDatabase.SaveAssets();
            Debug.Log("LS_VILLAGERS_OK");
        }

        /// <summary>A calmer idle for villagers who stand and talk: the Mixamo idle with its head turns, shoulder
        /// shrugs and arm swing damped towards their average, so nobody is caught mid-glance with arms wide.</summary>
        static AnimationClip CalmIdle(AnimationClip src)
        {
            const string path = "Assets/Art/Characters/Villagers/Villager_Idle.anim";
            var clip = new AnimationClip { name = "Villager_Idle" };
            foreach (var b in AnimationUtility.GetCurveBindings(src))
            {
                var curve = AnimationUtility.GetEditorCurve(src, b);
                string n = b.propertyName;
                float damp = n.Contains("Head") || n.Contains("Neck") ? 0.25f
                           : n.Contains("Arm") || n.Contains("Shoulder") || n.Contains("Forearm") || n.Contains("Hand") ? 0.45f
                           : n.Contains("Spine") || n.Contains("Chest") ? 0.5f : 1f;
                if (damp < 1f && curve.length > 1)
                {
                    float mean = 0f; foreach (var k in curve.keys) mean += k.value; mean /= curve.length;
                    if (n.Contains("Arm Down-Up")) mean -= 0.04f;                       // arms a touch closer to the body
                    var keys = curve.keys;
                    for (int i = 0; i < keys.Length; i++) { keys[i].value = mean + (keys[i].value - mean) * damp; keys[i].inTangent *= damp; keys[i].outTangent *= damp; }
                    curve.keys = keys;
                }
                AnimationUtility.SetEditorCurve(clip, b, curve);
            }
            var settings = AnimationUtility.GetAnimationClipSettings(src);
            settings.loopTime = true;
            AnimationUtility.SetAnimationClipSettings(clip, settings);
            AssetDatabase.DeleteAsset(path);
            AssetDatabase.CreateAsset(clip, path);
            Debug.Log($"LS_VILLAGER calm idle: {AnimationUtility.GetCurveBindings(clip).Length} curves, {clip.length:F1} s, humanoid {clip.humanMotion}");
            return clip;
        }

        static void Build(string name, string export, AnimatorController ac)
        {
            string dir = $"Assets/Art/Characters/{name}";
            string model = $"{dir}/{export}_GameReady.fbx", tex = $"{dir}/T_{name}_BaseColor.png";
            var mi = (ModelImporter)AssetImporter.GetAtPath(model);
            if (mi == null) { Debug.LogWarning("LS_VILLAGER missing " + model); return; }
            mi.animationType = ModelImporterAnimationType.Human;
            mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importAnimation = false;
            mi.importNormals = ModelImporterNormals.Calculate;      // pass 3: smooth hair and faces, crisp creases above 70 degrees
            mi.normalSmoothingAngle = 70f;
            mi.SaveAndReimport();
            var avatar = AssetDatabase.LoadAllAssetsAtPath(model).OfType<Avatar>().FirstOrDefault();
            Debug.Log($"LS_VILLAGER {name}: avatar valid {avatar && avatar.isValid}, human {avatar && avatar.isHuman}");
            var shader = Shader.Find("LastSkyfarer/StylisedCharacter");
            Material Mat(string n, float metallic, float spec)
            {
                string p = $"{dir}/{n}.mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(p);
                if (!m) { m = new Material(shader); AssetDatabase.CreateAsset(m, p); }
                m.shader = shader;
                m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(tex));
                m.SetFloat("_Metallic", metallic); m.SetFloat("_Specular", spec);
                m.SetColor("_ShadowTint", new Color(0.86f, 0.76f, 0.82f)); m.SetFloat("_Ambient", 1.35f);
                m.SetTexture("_MaskMap", LinearMask($"{dir}/T_{name}_Mask.png"));
                m.SetTexture("_BrushNoise", AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Art/Textures/T_BrushNoise.png"));
                EditorUtility.SetDirty(m);
                return m;
            }
            { var ti = (TextureImporter)AssetImporter.GetAtPath(tex); if (ti != null && ti.maxTextureSize != 4096) { ti.maxTextureSize = 4096; ti.SaveAndReimport(); } }   // pass 3: 4K atlas
            var cloth = Mat("M_" + name, 0f, 0.15f);
            cloth.SetFloat("_EyeBright", name == "Tessa" ? 1.5f : 1.15f);          // Tessa's green eyes read brighter
            var metal = Mat("M_" + name + "_Metal", 1f, 0.6f);
            var root = new GameObject(name);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(model));
            go.name = "Model";
            go.transform.SetParent(root.transform, false);
            go.transform.localPosition = new Vector3(0f, 0.06f, 0f);
            foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = i == 1 ? metal : cloth;
                r.sharedMaterials = mats;
            }
            var anim = go.GetComponent<Animator>() ?? go.AddComponent<Animator>();
            anim.runtimeAnimatorController = ac;
            anim.avatar = avatar;
            anim.applyRootMotion = false;
            anim.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
            // Character pass: hand-styled hair cards and proper eyes, grown at the bind pose.
            var style = name == "Tessa" ? HairStyle.CurlsLong : name == "Elara" ? HairStyle.CurlsMedium : name == "Bram" ? HairStyle.CombedBack : HairStyle.CombedShort;
            CharacterDetail.Build(go, anim, name, dir, CharacterDetail.LoadPng(tex), CharacterDetail.LoadPng($"{dir}/T_{name}_Mask.png"), style,
                                  beard: name == "Bram" || name == "Rowan");
            // Make sure the villager faces the prefab's forward (+Z): in the idle pose the toes must lie in front of
            // the ankles. If they do not, turn the model round, so turning to face Kieran shows the face, not the back.
            AnimationClip clip = ac.layers[0].stateMachine.defaultState.motion as AnimationClip;
            clip.SampleAnimation(go, 0f);
            var smr = go.GetComponentInChildren<SkinnedMeshRenderer>();
            var baked = new Mesh(); smr.BakeMesh(baked, true);
            Vector3 ankle = (anim.GetBoneTransform(HumanBodyBones.LeftFoot).position + anim.GetBoneTransform(HumanBodyBones.RightFoot).position) * 0.5f;
            float toes = 0f; int n = 0;
            foreach (var v in baked.vertices)
            {
                var w = smr.transform.TransformPoint(v);
                if (w.y < ankle.y - 0.04f) { toes += w.z - ankle.z; n++; }
            }
            toes /= Mathf.Max(n, 1);
            if (toes < 0f) go.transform.localRotation = Quaternion.Euler(0f, 180f, 0f);
            Debug.Log($"LS_VILLAGER {name}: toes {toes * 100f:F1} cm ahead of the ankles{(toes < 0f ? " - turned to face forward" : "")}");
            PrefabUtility.SaveAsPrefabAsset(root, $"{PrefabDir}/{name}.prefab");
            Object.DestroyImmediate(root);
        }

        /// <summary>The hair/skin/eye mask is data, not colour: import it linear, uncompressed.</summary>
        static Texture2D LinearMask(string path)
        {
            var ti = (TextureImporter)AssetImporter.GetAtPath(path);
            if (ti == null) { Debug.LogWarning("LS_MASK missing " + path); return null; }
            if (ti.sRGBTexture || ti.textureCompression != TextureImporterCompression.Uncompressed)
            {
                ti.sRGBTexture = false;
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                ti.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }
    }
}

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
        public static readonly (string speaker, string name, string export)[] Cast = { ("tavern", "Bram", "Bram_Holloway") };

        public static void Run()
        {
            Directory.CreateDirectory(PrefabDir);
            Directory.CreateDirectory(Path.GetDirectoryName(ControllerPath));
            var idle = AssetDatabase.LoadAllAssetsAtPath(IdlePath).OfType<AnimationClip>().First(a => !a.name.StartsWith("__preview"));
            AssetDatabase.DeleteAsset(ControllerPath);
            var ac = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            var st = ac.layers[0].stateMachine.AddState("Idle");
            st.motion = idle;
            ac.layers[0].stateMachine.defaultState = st;
            foreach (var (speaker, name, export) in Cast) Build(name, export, ac);
            AssetDatabase.SaveAssets();
            Debug.Log("LS_VILLAGERS_OK");
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
                EditorUtility.SetDirty(m);
                return m;
            }
            var cloth = Mat("M_" + name, 0f, 0.15f);
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
            PrefabUtility.SaveAsPrefabAsset(root, $"{PrefabDir}/{name}.prefab");
            Object.DestroyImmediate(root);
        }
    }
}

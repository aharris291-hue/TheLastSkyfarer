// The Last Skyfarer: builds Kieran for Unity in batchmode.
//   Unity.exe -batchmode -projectPath <project> -executeMethod LastSkyfarer.EditorTools.KieranSetup.Run -quit
// Humanoid avatar from his own skeleton, Mixamo clips retargeted through Humanoid, his horizontal glide pose,
// painted materials, an Animator (idle/walk/run blend, jump, fall, land, climb, glide) and the player prefab.
using System.Linq;
using LastSkyfarer.Player;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace LastSkyfarer.EditorTools
{
    public static class KieranSetup
    {
        const string Root = "Assets/Art/Characters/Kieran";
        const string ModelPath = Root + "/Model/Kieran_Thorn_GameReady.fbx";
        const string TexPath = Root + "/Model/T_Kieran_BaseColor.png";
        const string AnimDir = Root + "/Animations";
        const string ControllerPath = Root + "/Kieran.controller";
        const string PrefabPath = "Assets/Prefabs/Kieran.prefab";

        static readonly string[] Looping = { "Mixamo_Idle", "Mixamo_Walking", "Mixamo_Running", "Mixamo_FallingIdle", "Mixamo_ClimbingUpWall", "Kieran_Glide" };

        public static void Run()
        {
            // 1. Kieran's model: Humanoid avatar from his own skeleton.
            var mi = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
            mi.animationType = ModelImporterAnimationType.Human;
            mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;
            mi.importAnimation = false;
            mi.SaveAndReimport();
            var avatar = AssetDatabase.LoadAllAssetsAtPath(ModelPath).OfType<Avatar>().FirstOrDefault();
            Debug.Log($"LS_KIERAN avatar valid {avatar && avatar.isValid} human {avatar && avatar.isHuman} mapped {(avatar ? avatar.humanDescription.human.Length : 0)} bones");

            // 2. Animations: each Mixamo file builds its own Humanoid avatar; Humanoid retargets them onto Kieran.
            foreach (string path in AssetDatabase.FindAssets("t:Model", new[] { AnimDir }).Select(AssetDatabase.GUIDToAssetPath))
            {
                var ai = (ModelImporter)AssetImporter.GetAtPath(path);
                string name = System.IO.Path.GetFileNameWithoutExtension(path);
                ai.animationType = ModelImporterAnimationType.Human;
                ai.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;   // every file maps its own skeleton; Humanoid retargets
                ai.importAnimation = true;
                ai.materialImportMode = ModelImporterMaterialImportMode.None;
                var clips = ai.defaultClipAnimations;
                foreach (var c in clips)
                {
                    c.name = name;
                    c.loopTime = Looping.Contains(name);
                    c.lockRootRotation = c.lockRootHeightY = c.lockRootPositionXZ = true;   // in place: the controller moves him
                    c.keepOriginalOrientation = c.keepOriginalPositionY = c.keepOriginalPositionXZ = true;
                }
                ai.clipAnimations = clips;
                ai.SaveAndReimport();
                var clip = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().FirstOrDefault(a => !a.name.StartsWith("__preview"));
                var av = AssetDatabase.LoadAllAssetsAtPath(path).OfType<Avatar>().FirstOrDefault();
                Debug.Log($"LS_KIERAN clip {name}: {(clip ? clip.length : -1):F2} s, humanoid {(clip && clip.humanMotion)}, avatar ok {(av && av.isValid)}");
            }

            // 3. Painted materials (URP Lit) from the baked atlas.
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexPath);
            Material Mat(string n, float metallic, float smooth)
            {
                string p = Root + "/" + n + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(p);
                if (!m) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(m, p); }
                m.SetTexture("_BaseMap", tex);
                m.SetFloat("_Metallic", metallic);
                m.SetFloat("_Smoothness", smooth);
                EditorUtility.SetDirty(m);
                return m;
            }
            var cloth = Mat("M_Kieran", 0f, 0.25f);
            var metal = Mat("M_Kieran_Metal", 1f, 0.6f);

            // 4. Animator.
            AnimationClip C(string n) => AssetDatabase.LoadAllAssetsAtPath($"{AnimDir}/{n}.fbx").OfType<AnimationClip>().First(a => !a.name.StartsWith("__preview"));
            AssetDatabase.DeleteAsset(ControllerPath);
            var ac = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            ac.AddParameter("Speed", AnimatorControllerParameterType.Float);
            ac.AddParameter("Grounded", AnimatorControllerParameterType.Bool);
            ac.AddParameter("Gliding", AnimatorControllerParameterType.Bool);
            ac.AddParameter("Climbing", AnimatorControllerParameterType.Bool);
            ac.AddParameter("ClimbSpeed", AnimatorControllerParameterType.Float);
            ac.AddParameter("Jump", AnimatorControllerParameterType.Trigger);
            var sm = ac.layers[0].stateMachine;
            var loco = ac.CreateBlendTreeInController("Locomotion", out BlendTree tree, 0);
            tree.blendParameter = "Speed";
            tree.useAutomaticThresholds = false;
            tree.AddChild(C("Mixamo_Idle"), 0f);
            tree.AddChild(C("Mixamo_Walking"), 1.8f);
            tree.AddChild(C("Mixamo_Running"), 4.5f);
            var sprint = tree.children.ToList();            // sprinting plays the run a little faster
            tree.AddChild(C("Mixamo_Running"), 6.5f);
            var ch = tree.children; ch[3].timeScale = 1.35f; tree.children = ch;
            var jump = sm.AddState("JumpUp"); jump.motion = C("Mixamo_JumpingUp");
            var fall = sm.AddState("Falling"); fall.motion = C("Mixamo_FallingIdle");
            var land = sm.AddState("Land"); land.motion = C("Mixamo_FallingToLanding");
            var glide = sm.AddState("Glide"); glide.motion = C("Kieran_Glide");
            var climb = sm.AddState("Climb"); climb.motion = C("Mixamo_ClimbingUpWall"); climb.speedParameter = "ClimbSpeed"; climb.speedParameterActive = true;
            sm.defaultState = loco;

            AnimatorStateTransition T(AnimatorState from, AnimatorState to, float dur, bool exit = false)
            {
                var t = from.AddTransition(to);
                t.hasExitTime = exit; t.exitTime = exit ? 0.85f : 0f; t.duration = dur; t.hasFixedDuration = true;
                return t;
            }
            // From anywhere: glide and climb take priority.
            var anyGlide = sm.AddAnyStateTransition(glide); anyGlide.AddCondition(AnimatorConditionMode.If, 0, "Gliding"); anyGlide.duration = 0.2f; anyGlide.canTransitionToSelf = false;
            var anyClimb = sm.AddAnyStateTransition(climb); anyClimb.AddCondition(AnimatorConditionMode.If, 0, "Climbing"); anyClimb.duration = 0.15f; anyClimb.canTransitionToSelf = false;
            T(glide, fall, 0.25f).AddCondition(AnimatorConditionMode.IfNot, 0, "Gliding");
            var cl = T(climb, loco, 0.2f); cl.AddCondition(AnimatorConditionMode.IfNot, 0, "Climbing"); cl.AddCondition(AnimatorConditionMode.If, 0, "Grounded");
            var cf = T(climb, fall, 0.2f); cf.AddCondition(AnimatorConditionMode.IfNot, 0, "Climbing"); cf.AddCondition(AnimatorConditionMode.IfNot, 0, "Grounded");
            T(loco, jump, 0.1f).AddCondition(AnimatorConditionMode.If, 0, "Jump");
            T(loco, fall, 0.2f).AddCondition(AnimatorConditionMode.IfNot, 0, "Grounded");
            T(jump, fall, 0.2f, exit: true);
            T(jump, land, 0.1f).AddCondition(AnimatorConditionMode.If, 0, "Grounded");
            T(fall, land, 0.1f).AddCondition(AnimatorConditionMode.If, 0, "Grounded");
            var lm = T(land, loco, 0.15f); lm.AddCondition(AnimatorConditionMode.Greater, 0.5f, "Speed");   // running off a landing
            T(land, loco, 0.2f, exit: true);
            T(land, fall, 0.1f).AddCondition(AnimatorConditionMode.IfNot, 0, "Grounded");
            AssetDatabase.SaveAssets();

            // 5. Player prefab: controller and collision for 5 ft 8 in, model as a child with the Animator.
            System.IO.Directory.CreateDirectory("Assets/Prefabs");
            var root = new GameObject("Kieran");
            var cc = root.AddComponent<CharacterController>();
            cc.height = 1.76f; cc.radius = 0.32f; cc.center = new Vector3(0f, 0.89f, 0f); cc.stepOffset = 0.35f; cc.skinWidth = 0.03f;
            root.AddComponent<KieranController>();
            root.AddComponent<Traversal>();
            var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath));
            model.name = "Model";
            model.transform.SetParent(root.transform, false);
            model.transform.localPosition = new Vector3(0f, 0.06f, 0f);   // Humanoid retargeting set his soles 6-9 cm under the controller base
            foreach (var r in model.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = i == 1 ? metal : cloth;
                r.sharedMaterials = mats;
                r.updateWhenOffscreen = false;
            }
            var anim = model.GetComponent<Animator>() ?? model.AddComponent<Animator>();
            anim.runtimeAnimatorController = ac;
            anim.avatar = avatar;
            anim.applyRootMotion = false;
            anim.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
            var driver = root.AddComponent<KieranAnimator>();
            driver.Animator = anim;
            var b = new Bounds(); bool first = true;
            foreach (var r in model.GetComponentsInChildren<Renderer>()) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
            Debug.Log($"LS_KIERAN model height {b.size.y:F3} m, bottom {b.min.y:F3}, width {b.size.x:F3}");
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            Debug.Log("LS_KIERAN_SETUP_OK");
        }
    }
}

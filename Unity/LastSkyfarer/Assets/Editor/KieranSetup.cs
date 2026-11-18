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
            mi.importNormals = ModelImporterNormals.Calculate;      // pass 3: smooth hair and faces, crisp creases above 70 degrees
            mi.normalSmoothingAngle = 70f;
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
            { var ti = (TextureImporter)AssetImporter.GetAtPath(TexPath); if (ti.maxTextureSize != 4096) { ti.maxTextureSize = 4096; ti.SaveAndReimport(); } }   // pass 3: 4K atlas
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(TexPath);
            Material Mat(string n, float metallic, float smooth)
            {
                string p = Root + "/" + n + ".mat";
                var m = AssetDatabase.LoadAssetAtPath<Material>(p);
                var shader = Shader.Find("LastSkyfarer/StylisedCharacter");      // polish pass 1: stylised shading
                if (!m) { m = new Material(shader); AssetDatabase.CreateAsset(m, p); }
                m.shader = shader;
                m.SetTexture("_BaseMap", tex);
                m.SetFloat("_Metallic", metallic);
                m.SetFloat("_Specular", 0.1f + smooth * 0.4f);
                m.SetColor("_ShadowTint", new Color(0.86f, 0.76f, 0.82f)); m.SetFloat("_Ambient", 1.35f);
                m.SetTexture("_MaskMap", LinearMask(Root + "/Model/T_Kieran_Mask.png"));
                m.SetTexture("_BrushNoise", AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Art/Textures/T_BrushNoise.png"));
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
            var acLayers = ac.layers; acLayers[0].iKPass = true; ac.layers = acLayers;   // hands to the glider bar
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
            // Character pass: hair cards (tight curls) and proper eyes, grown at the bind pose.
            CharacterDetail.Build(model, anim, "Kieran", Root, CharacterDetail.LoadPng(TexPath), CharacterDetail.LoadPng(Root + "/Model/T_Kieran_Mask.png"),
                                  HairStyle.CurlTufts, false);
            var driver = root.AddComponent<KieranAnimator>();
            driver.Animator = anim;
            var b = new Bounds(); bool first = true;
            foreach (var r in model.GetComponentsInChildren<Renderer>()) { if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds); }
            Debug.Log($"LS_KIERAN model height {b.size.y:F3} m, bottom {b.min.y:F3}, width {b.size.x:F3}");
            BuildGlider(root, model, anim, C("Kieran_Glide"));
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            Object.DestroyImmediate(root);
            AssetDatabase.SaveAssets();
            Debug.Log("LS_KIERAN_SETUP_OK");
        }

        // ------------------------------------------------------------ Elias's glider and the grip (glide_pose.py measurements)
        static void BuildGlider(GameObject root, GameObject model, Animator anim, AnimationClip glide)
        {
            // Where his shoulders are in the glide pose, relative to the player root (+Z is the way he flies).
            glide.SampleAnimation(model, 0f);
            Vector3 L(HumanBodyBones bone) => root.transform.InverseTransformPoint(anim.GetBoneTransform(bone).position);
            Vector3 shoulders = (L(HumanBodyBones.LeftUpperArm) + L(HumanBodyBones.RightUpperArm)) * 0.5f;
            Debug.Log($"LS_KIERAN glide pose: shoulders {shoulders}, head {L(HumanBodyBones.Head)}, hips {L(HumanBodyBones.Hips)}, hands {L(HumanBodyBones.LeftHand)} {L(HumanBodyBones.RightHand)}");
            Vector3 bar = shoulders + new Vector3(0f, -0.38f, 0.30f);      // 30 cm ahead of and 38 cm below the shoulders
            const float half = 0.26f;                                       // a shoulder-width grip

            var glider = new GameObject("Glider");
            glider.transform.SetParent(root.transform, false);
            var sail = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/MI_Sailcloth.mat");
            var wood = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/MI_Wood.mat");
            var brass = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Materials/MI_Brass.mat");
            var rodMesh = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/Art/Generated/Cylinder48.asset") ?? Resources.GetBuiltinResource<Mesh>("Cylinder.fbx");
            void Rod(string name, Vector3 a, Vector3 c, float d, Material m)
            {
                var go = new GameObject(name);
                go.transform.SetParent(glider.transform, false);
                go.transform.localPosition = (a + c) * 0.5f;
                go.transform.localRotation = Quaternion.FromToRotation(Vector3.up, c - a);
                go.transform.localScale = new Vector3(d, (c - a).magnitude, d);
                go.AddComponent<MeshFilter>().sharedMesh = rodMesh;
                go.AddComponent<MeshRenderer>().sharedMaterial = m;
            }
            Vector3 apex = bar + new Vector3(0f, 0.95f, 0.25f);
            Vector3 nose = apex + new Vector3(0f, 0.10f, 1.30f), tail = apex + new Vector3(0f, 0.05f, -1.90f);
            Vector3 tipL = apex + new Vector3(-3.4f, 0.28f, -1.55f), tipR = apex + new Vector3(3.4f, 0.28f, -1.55f);
            Rod("ControlBar", bar + Vector3.left * 0.45f, bar + Vector3.right * 0.45f, 0.035f, brass);
            Rod("Upright_L", bar + Vector3.left * 0.45f, apex, 0.03f, wood);
            Rod("Upright_R", bar + Vector3.right * 0.45f, apex, 0.03f, wood);
            Rod("Keel", nose, tail, 0.045f, wood);
            Rod("LeadingEdge_L", nose, tipL, 0.04f, wood);
            Rod("LeadingEdge_R", nose, tipR, 0.04f, wood);
            Rod("CrossSpar", Vector3.Lerp(nose, tipL, 0.55f), Vector3.Lerp(nose, tipR, 0.55f), 0.03f, wood);
            // The sail: two billowing panels, drawn from both sides.
            var mesh = new Mesh { name = "GliderSail" };
            Vector3 billowL = Vector3.Lerp(Vector3.Lerp(nose, tipL, 0.5f), tail, 0.45f) + Vector3.up * 0.22f;
            Vector3 billowR = Vector3.Lerp(Vector3.Lerp(nose, tipR, 0.5f), tail, 0.45f) + Vector3.up * 0.22f;
            var v = new[] { nose, tipL, tail, billowL, tipR, billowR };
            var verts = new System.Collections.Generic.List<Vector3>();
            var tris = new System.Collections.Generic.List<int>();
            void Tri(Vector3 a, Vector3 c, Vector3 e) { int i = verts.Count; verts.AddRange(new[] { a, c, e, a, e, c }); tris.AddRange(new[] { i, i + 1, i + 2, i + 3, i + 4, i + 5 }); }
            Tri(nose, billowL, tipL); Tri(tipL, billowL, tail); Tri(nose, tail, billowL);
            Tri(nose, tipR, billowR); Tri(tipR, tail, billowR); Tri(nose, billowR, tail);
            mesh.SetVertices(verts); mesh.SetTriangles(tris, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            string meshPath = Root + "/GliderSail.asset";
            AssetDatabase.DeleteAsset(meshPath);
            AssetDatabase.CreateAsset(mesh, meshPath);
            var sailGo = new GameObject("Sail");
            sailGo.transform.SetParent(glider.transform, false);
            sailGo.AddComponent<MeshFilter>().sharedMesh = mesh;
            sailGo.AddComponent<MeshRenderer>().sharedMaterial = sail;

            // Grips: wrists just behind and above the bar so the palms close over it, fingers forward and curled down.
            Transform Grip(string name, float side, float yaw)
            {
                var t = new GameObject(name).transform;
                t.SetParent(root.transform, false);
                t.localPosition = bar + new Vector3(side * half, 0.06f, -0.05f);
                t.localRotation = Quaternion.AngleAxis(25f, Vector3.right) * Quaternion.AngleAxis(yaw, Vector3.up);
                return t;
            }
            var rig = model.AddComponent<KieranGlideRig>();
            rig.Kieran = root.GetComponent<KieranController>();
            rig.Glider = glider;
            rig.LeftGrip = Grip("Grip_L", -1f, 90f);
            rig.RightGrip = Grip("Grip_R", 1f, -90f);
            glider.SetActive(false);
            // Back to the bind pose before saving the prefab.
            AssetDatabase.LoadAllAssetsAtPath(Root + "/Animations/Mixamo_Idle.fbx").OfType<AnimationClip>().First(a => !a.name.StartsWith("__preview")).SampleAnimation(model, 0f);
            Debug.Log($"LS_KIERAN glider: bar {bar}, apex {apex}, span {(tipR - tipL).magnitude:F1} m");
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

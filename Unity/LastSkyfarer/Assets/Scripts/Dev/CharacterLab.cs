// The Last Skyfarer: neutral-light character lab (-LSCharacterLab [-LSLabTag <name>]). For honest before/after
// comparisons of the character models: post-processing off, no fog, no sky, a flat grey backdrop and floor, one white
// key light at a fixed angle and a flat neutral ambient. Kieran stands in his idle animation and is photographed from
// the front, three-quarter, side and back, plus the face, the hands and the hair. Saves to
// <persistentDataPath>/CharacterLab/<tag>/ and quits.
using System.Collections;
using System.IO;
using LastSkyfarer.World;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace LastSkyfarer.Dev
{
    public class CharacterLab : MonoBehaviour
    {
        public BrindleLevel Level;
        static readonly Vector3 Spot = new Vector3(0f, 600f, 2000f);   // far from the island and its lights

        IEnumerator Start()
        {
            string tag = "lab";
            var args = System.Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++) if (args[i] == "-LSLabTag") tag = args[i + 1];
            string outDir = Path.Combine(Application.persistentDataPath, "CharacterLab", tag);
            Directory.CreateDirectory(outDir);
            Level.Story.SetFlag("opening_seen");
            Level.Hud.ShowHud = false;
            yield return null;

            // Neutral studio: grey floor and backdrop, one white key light, flat grey ambient, nothing else.
            var tod = FindAnyObjectByType<TimeOfDayDirector>();
            if (tod) tod.enabled = false;
            foreach (var v in FindObjectsByType<Volume>(FindObjectsSortMode.None)) v.enabled = false;
            foreach (var l in FindObjectsByType<Light>(FindObjectsSortMode.None)) l.enabled = false;
            RenderSettings.fog = false;
            RenderSettings.skybox = null;
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.42f, 0.42f, 0.42f);
            DynamicGI.UpdateEnvironment();
            var key = new GameObject("LabKey").AddComponent<Light>();
            key.type = LightType.Directional;
            key.color = Color.white;
            key.intensity = 1.6f;
            key.shadows = LightShadows.Soft;
            key.transform.rotation = Quaternion.Euler(35f, 150f, 0f);   // high, from the camera's front-left
            // Painterly is always in the build (URP/Lit may be stripped): plain grey, no strokes, no rim, no shading ramp.
            var grey = new Material(Shader.Find("LastSkyfarer/Painterly"));
            foreach (var p in new[] { "_ColorA", "_ColorB", "_TopColorA", "_TopColorB" }) grey.SetColor(p, new Color(0.5f, 0.5f, 0.5f));
            foreach (var p in new[] { "_TopAmount", "_StrokeMix", "_ShadeAmount", "_Bump", "_Specular", "_Rim" }) grey.SetFloat(p, 0f);
            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.transform.position = Spot + new Vector3(0f, -0.5f, 0f);
            floor.transform.localScale = new Vector3(30f, 1f, 30f);
            floor.GetComponent<Renderer>().sharedMaterial = grey;
            var cam = Level.Cam;
            Level.CameraRig.enabled = false;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.36f, 0.37f, 0.39f);
            var data = cam.GetComponent<UniversalAdditionalCameraData>();
            if (data) { data.renderPostProcessing = false; data.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing; }
            cam.farClipPlane = 60f;

            var k = Level.Kieran;
            k.Stow();
            k.Teleport(Spot, 180f);   // facing -Z, towards the camera
            yield return new WaitForSeconds(1.5f);
            var an = k.GetComponentInChildren<Animator>();
            if (an) an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            Transform B(HumanBodyBones b) => an ? an.GetBoneTransform(b) : k.transform;
            Vector3 feet = k.transform.position;
            Vector3 front = k.transform.forward;

            // Full body: front, three-quarter, side, back.
            foreach (var (name, yaw) in new[] { ("1_front", 0f), ("2_three_quarter", 35f), ("3_side", 90f), ("4_back", 180f) })
                yield return Shoot(outDir, name, feet + Vector3.up * 0.9f, front, yaw, 3.4f, 34f);
            // Head: front and three-quarter.
            Vector3 head = B(HumanBodyBones.Head).position + Vector3.up * 0.06f;
            yield return Shoot(outDir, "5_face_front", head, front, 0f, 0.75f, 30f);
            yield return Shoot(outDir, "6_face_three_quarter", head, front, 40f, 0.75f, 30f);
            yield return Shoot(outDir, "7_hair_back", head + Vector3.up * 0.04f, front, 150f, 0.8f, 30f);
            // Hands and torso detail.
            Vector3 hand = B(HumanBodyBones.RightHand).position;
            yield return Shoot(outDir, "8_hand", hand, front, 15f, 0.75f, 30f);   // from the front: the stowed glider is behind him
            Vector3 chest = B(HumanBodyBones.Chest).position;
            yield return Shoot(outDir, "9_jacket", chest, front, 25f, 1.3f, 32f);
            Debug.Log("LS_LAB_DONE " + outDir);
            Application.Quit();
        }

        IEnumerator Shoot(string dir, string name, Vector3 target, Vector3 front, float yaw, float distance, float fov)
        {
            var cam = Level.Cam;
            Vector3 d = Quaternion.Euler(0f, yaw, 0f) * front;
            cam.transform.position = target + d * distance + Vector3.up * 0.05f;
            cam.transform.LookAt(target);
            cam.fieldOfView = fov;
            yield return new WaitForSeconds(0.6f);
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.Combine(dir, name + ".png"));
            Debug.Log("LS_LAB shot " + name);
            yield return null;
        }
    }
}

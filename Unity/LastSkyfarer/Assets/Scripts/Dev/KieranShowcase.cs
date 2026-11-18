// The Last Skyfarer: development check (-LSKieranShowcase). Builds a small test range, runs Kieran through idle,
// running, jumping, gliding and climbing, takes a screenshot of each and logs his measured height and the frame rate.
using System.Collections;
using System.IO;
using LastSkyfarer.Player;
using UnityEngine;

namespace LastSkyfarer.Dev
{
    public class KieranShowcase : MonoBehaviour
    {
        public GameObject KieranPrefab;
        KieranController k;
        Camera cam;
        string outDir;

        static GameObject Box(string name, Vector3 centre, Vector3 size, Color colour, bool climbable = false)
        {
            var b = GameObject.CreatePrimitive(PrimitiveType.Cube);
            b.name = name;
            b.transform.position = centre;
            b.transform.localScale = size;
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { color = colour };
            b.GetComponent<Renderer>().sharedMaterial = m;
            if (climbable) b.AddComponent<Climbable>();
            return b;
        }

        IEnumerator Start()
        {
            outDir = Path.Combine(Application.persistentDataPath, "Showcase");
            Directory.CreateDirectory(outDir);
            Box("Ground", new Vector3(0f, -0.5f, 100f), new Vector3(400f, 1f, 600f), new Color(0.42f, 0.6f, 0.3f));
            Box("Cliff", new Vector3(0f, 15f, -20f), new Vector3(12f, 30f, 12f), new Color(0.6f, 0.52f, 0.42f));
            Box("ClimbWall", new Vector3(20f, 3f, 6f), new Vector3(6f, 6f, 2f), new Color(0.55f, 0.48f, 0.4f), climbable: true);
            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 1.3f; sun.color = new Color(1f, 0.96f, 0.88f);
            sun.transform.rotation = Quaternion.Euler(45f, -30f, 0f);
            sun.shadows = LightShadows.Soft;
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.62f, 0.72f, 0.85f);
            RenderSettings.ambientEquatorColor = new Color(0.55f, 0.55f, 0.5f);
            RenderSettings.ambientGroundColor = new Color(0.3f, 0.32f, 0.25f);
            cam = new GameObject("Camera").AddComponent<Camera>();
            cam.fieldOfView = 45f;
            cam.backgroundColor = new Color(0.62f, 0.78f, 0.92f);
            cam.clearFlags = CameraClearFlags.SolidColor;

            k = Instantiate(KieranPrefab).GetComponent<KieranController>();
            k.Teleport(new Vector3(0f, 0.05f, 0f), 180f);
            yield return new WaitForSeconds(1f);

            // Height check: bake the skinned mesh in the idle pose.
            var smr = k.GetComponentInChildren<SkinnedMeshRenderer>();
            var baked = new Mesh();
            smr.BakeMesh(baked, true);
            float minY = float.MaxValue, maxY = float.MinValue;
            foreach (var v in baked.vertices) { float y = smr.transform.TransformPoint(v).y; minY = Mathf.Min(minY, y); maxY = Mathf.Max(maxY, y); }
            Debug.Log($"LS_SHOWCASE height {maxY - minY:F3} m (feet at {minY - k.transform.position.y:F3} m from the controller base)");

            yield return Shot("1_idle", () => Frame(k.transform.position, 20f, 3.4f, 0.6f), 1.5f);

            k.Input.ScriptedMove = new Vector2(0f, 1f);
            k.CameraYawSource = null;
            k.transform.rotation = Quaternion.Euler(0f, 0f, 0f);
            yield return Shot("2_running", () => Frame(k.transform.position, 45f, 4.2f, 0.6f), 1.6f);
            k.Input.ScriptedMove = Vector2.zero;
            yield return new WaitForSeconds(0.6f);

            k.JumpPressed();
            yield return Shot("3_jumping", () => Frame(k.transform.position, 60f, 4.2f, 0.6f), 0.28f);
            yield return new WaitForSeconds(1.5f);

            // Glide: off the cliff top, then look from the side and three-quarter.
            k.Teleport(new Vector3(0f, 30.1f, -20f), 0f);
            yield return new WaitForSeconds(0.4f);
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            while (k.Mode != MoveMode.Falling) yield return null;
            yield return new WaitForSeconds(0.25f);
            k.Input.ScriptedMove = Vector2.zero;
            k.TryDeploy();
            yield return Shot("4_gliding_side", () => Frame(k.transform.position, 90f, 5.5f, 0.4f), 1.5f);
            yield return Shot("5_gliding_front", () => Frame(k.transform.position, 35f, 5.5f, 1.4f), 0.6f);
            var grip = k.GetComponentInChildren<KieranGlideRig>();
            if (grip) { var e = grip.GripError(); Debug.Log($"LS_SHOWCASE grip left {e.x * 100f:F1} cm, right {e.y * 100f:F1} cm from the bar"); }
            yield return Shot("5b_gliding_above", () => Frame(k.transform.position, 150f, 6.5f, 3.0f), 0.3f);
            while (k.Mode == MoveMode.Gliding) yield return null;
            yield return new WaitForSeconds(0.8f);

            // Climb the climbable wall.
            k.Teleport(new Vector3(20f, 0.05f, 2f), 0f);
            yield return new WaitForSeconds(0.4f);
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            var t = k.GetComponent<Traversal>();
            float wait = 0f;
            while (t.State != TraversalState.Climbing && wait < 3f) { wait += Time.deltaTime; yield return null; }
            yield return Shot("6_climbing", () => Frame(k.transform.position, 205f, 4.5f, 1.0f), 1.2f);
            k.Input.ScriptedMove = Vector2.zero;

            // Frame rate: 10 s of running and gliding around the range.
            k.Teleport(new Vector3(0f, 0.05f, 30f), 0f);
            k.Input.ScriptedMove = new Vector2(0.3f, 1f);
            int frames = 0; float time = 0f;
            while (time < 10f) { time += Time.unscaledDeltaTime; frames++; Frame(k.transform.position, 160f, 4f, 1f); yield return null; }
            Debug.Log($"LS_SHOWCASE_FPS quality {QualitySettings.names[QualitySettings.GetQualityLevel()]}: average {frames / time:F1} fps");
            Debug.Log("LS_SHOWCASE_DONE " + outDir);
            Application.Quit();
        }

        void Frame(Vector3 target, float yawFromForward, float distance, float height)
        {
            Quaternion q = Quaternion.Euler(0f, k.transform.eulerAngles.y + yawFromForward, 0f);
            Vector3 pos = target + q * Vector3.forward * distance + Vector3.up * (height + 0.6f);
            cam.transform.position = pos;
            cam.transform.LookAt(target + Vector3.up * 0.9f);
        }

        IEnumerator Shot(string name, System.Action frame, float after)
        {
            float t = 0f;
            while (t < after) { t += Time.deltaTime; frame(); yield return null; }
            frame();
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.Combine(outDir, name + ".png"));
            Debug.Log("LS_SHOWCASE shot " + name);
            yield return null;
        }
    }
}

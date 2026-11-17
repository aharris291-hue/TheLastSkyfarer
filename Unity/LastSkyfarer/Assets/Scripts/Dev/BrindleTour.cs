// The Last Skyfarer: development tour of Brindle Isle (-LSBrindleTour). Uses the real gameplay camera and Kieran:
// the village square in the morning, a glide off the Bluff at dawn, the village at sunset and at night, and the view
// from the Upper Cliffs. Saves a screenshot of each, measures the frame rate running and gliding, then quits.
using System.Collections;
using System.IO;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using LastSkyfarer.World;
using UnityEngine;

namespace LastSkyfarer.Dev
{
    public class BrindleTour : MonoBehaviour
    {
        public BrindleLevel Level;
        string outDir;

        KieranController K => Level.Kieran;
        ThirdPersonCamera Rig => Level.CameraRig;

        IEnumerator Start()
        {
            outDir = Path.Combine(Application.persistentDataPath, "BrindleTour");
            Directory.CreateDirectory(outDir);
            var story = Level.Story;
            story.SetFlag("opening_seen");          // no conversations in the pictures
            Level.Hud.ShowHud = false;
            yield return null;

            // 1. The village square, morning.
            yield return Place("Morning", new Vector3(-5f, 0.05f, -15f), 25f, 7f, 10f);
            yield return Shot("1_village_square_morning", 2.5f);

            // 2. Gliding off the Bluff at dawn, east along the impossible current.
            story.SetFlag("has_glider"); story.SetFlag("piko_joined"); story.SetFlag("compass_active");
            Level.TimeOfDay.Apply("Dawn", true);
            Rig.Distance = 3.2f;
            K.Teleport(new Vector3(686f, 21.5f, 60f), 90f);
            Rig.Yaw = 55f; Rig.Pitch = 8f;
            yield return new WaitForSeconds(0.35f);
            K.TryDeploy();
            float t = 0f;
            while (t < 3f) { t += Time.deltaTime; Rig.Yaw = Mathf.LerpAngle(Rig.Yaw, 60f, Time.deltaTime); yield return null; }
            yield return Shot("2_gliding_dawn", 0f);
            Debug.Log($"LS_TOUR glide mode {K.Mode}, height {K.transform.position.y:F1} m, speed {K.GlideState.Speed:F1} m/s");
            yield return new WaitForSeconds(1.5f);
            yield return Shot("2b_gliding_dawn_back", 0f, () => { Rig.Yaw = 250f; Rig.Pitch = 15f; });

            // 3. The village at sunset, looking towards the low sun.
            yield return Place("Sunset", new Vector3(-20f, 0.05f, -24f), 62f, 6f, 9f);
            yield return Shot("3_village_sunset", 2.5f);

            // 4. Night: lanterns lit.
            yield return Place("Night", new Vector3(-5f, 0.05f, -15f), 25f, 7f, 10f);
            yield return Shot("4_village_night", 2.5f);

            // 5. The opening view from the Upper Cliffs, morning.
            yield return Place("Morning", Level.PlayerStart.position, Level.PlayerStart.eulerAngles.y - 160f, 4f, 6f, Level.PlayerStart.eulerAngles.y);
            yield return Shot("5_upper_cliffs_view", 2.5f);

            // Character close-ups: Bram at the Windsong Tavern, then Kieran in the square (morning light).
            var bram = Level.Story.Database.FindInteractable("NPC_Bram");
            if (bram != null)
            {
                Level.TimeOfDay.Apply("Morning", true);
                K.Teleport(bram.Position + Quaternion.Euler(0f, bram.Yaw, 0f) * new Vector3(1.6f, 0f, 2.4f), bram.Yaw + 200f);
                // Aim from where he actually faces (the Humanoid body direction), not from the placement yaw.
                float facing = bram.Yaw;
                foreach (var an in FindObjectsByType<Animator>(FindObjectsSortMode.None))
                    if (an.isHuman && !an.GetComponentInParent<KieranController>() && Vector3.Distance(an.transform.position, bram.Position) < 2f)
                    {
                        an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                        yield return null;
                        // The head's centroid sits behind the face (hair, ponytail).
                        var head = an.GetBoneTransform(HumanBodyBones.Head);
                        var smr = an.GetComponentInChildren<SkinnedMeshRenderer>();
                        var baked = new Mesh(); smr.BakeMesh(baked, true);
                        Vector3 sum = Vector3.zero; int count = 0;
                        foreach (var vtx in baked.vertices)
                        {
                            Vector3 w = smr.transform.TransformPoint(vtx);
                            if (Vector3.Distance(w, head.position + Vector3.up * 0.05f) < 0.16f) { sum += w; count++; }
                        }
                        Vector3 f = sum / Mathf.Max(count, 1) - head.position; f.y = 0f;
                        if (f.sqrMagnitude > 1e-6f) facing = Quaternion.LookRotation(f).eulerAngles.y + 180f;   // the hair and ponytail outweigh the face: it is the other way
                        Debug.Log($"LS_TOUR facing Bram: placed {bram.Yaw:F0}, body faces {facing:F0}");
                    }
                yield return CloseUp("6_bram_closeup", bram.Position, facing + 18f, 2.3f, 1.55f);
                yield return CloseUp("6b_bram_full", bram.Position, facing - 30f, 3.6f, 1.0f);
            }
            yield return Place("Morning", new Vector3(-5f, 0.05f, -15f), 25f, 7f, 10f, 25f);
            yield return CloseUp("7_kieran_closeup", K.transform.position, 25f + 20f, 2.0f, 1.35f);
            Rig.enabled = true;

            // Frame rate: 10 s running round the square with the camera turning, then 8 s gliding.
            yield return Place("Morning", new Vector3(0f, 0.05f, -18f), 0f, 12f, 3.2f, 90f);
            K.Input.ScriptedMove = new Vector2(0f, 1f);
            K.Input.ScriptedLook = new Vector2(0.35f, 0f);
            yield return MeasureFor(10f, v => runFps = v);
            K.Input.ScriptedMove = null; K.Input.ScriptedLook = null;
            Level.TimeOfDay.Apply("Morning", true);
            K.Teleport(new Vector3(686f, 21.5f, 60f), 90f);
            Rig.Yaw = 90f;
            yield return new WaitForSeconds(0.35f);
            K.TryDeploy();
            float glideFps = 0f;
            yield return MeasureFor(8f, v => glideFps = v);
            Debug.Log($"LS_TOUR_FPS quality {QualitySettings.names[QualitySettings.GetQualityLevel()]}, {Screen.width}x{Screen.height}, cap {Application.targetFrameRate}: running {runFps:F1} fps, gliding {glideFps:F1} fps (worst frame {worst * 1000f:F0} ms)");
            // Headroom: the same square view with the frame cap off.
            int cap = Application.targetFrameRate, vsync = QualitySettings.vSyncCount;
            Application.targetFrameRate = -1; QualitySettings.vSyncCount = 0;
            yield return Place("Morning", new Vector3(-5f, 0.05f, -15f), 25f, 7f, 4f);
            float free = 0f;
            yield return MeasureFor(6f, v => free = v);
            yield return Place("Sunset", new Vector3(-20f, 0.05f, -24f), 62f, 6f, 4f);
            float freeSunset = 0f;
            yield return MeasureFor(6f, v => freeSunset = v);
            Application.targetFrameRate = cap; QualitySettings.vSyncCount = vsync;
            Debug.Log($"LS_TOUR_HEADROOM uncapped square morning {free:F1} fps, sunset {freeSunset:F1} fps");
            Debug.Log("LS_TOUR_DONE " + outDir);
            Application.Quit();
        }

        float runFps, worst;

        IEnumerator MeasureFor(float seconds, System.Action<float> result)
        {
            yield return null;
            int frames = 0; float time = 0f;
            while (time < seconds) { float dt = Time.unscaledDeltaTime; time += dt; frames++; worst = Mathf.Max(worst, dt); yield return null; }
            result(frames / time);
        }

        IEnumerator CloseUp(string name, Vector3 at, float yawFromFront, float distance, float lookHeight)
        {
            Rig.enabled = false;
            var cam = Level.Cam.transform;
            Vector3 dir = Quaternion.Euler(0f, yawFromFront, 0f) * Vector3.forward;
            Vector3 target = at + Vector3.up * lookHeight;
            cam.position = target + dir * distance + Vector3.up * 0.15f;
            cam.LookAt(target);
            Level.Cam.fieldOfView = 40f;
            yield return Shot(name, 1.2f);
            Level.Cam.fieldOfView = 80f;
        }

        IEnumerator Place(string tod, Vector3 at, float yaw, float pitch, float distance, float kieranYaw = float.NaN)
        {
            Level.TimeOfDay.Apply(tod, true);
            K.Stow();
            K.Teleport(at, float.IsNaN(kieranYaw) ? yaw : kieranYaw);
            Rig.Yaw = yaw; Rig.Pitch = pitch; Rig.Distance = distance;
            yield return new WaitForSeconds(0.5f);
        }

        IEnumerator Shot(string name, float settle, System.Action frame = null)
        {
            float t = 0f;
            while (t < settle) { t += Time.deltaTime; frame?.Invoke(); yield return null; }
            frame?.Invoke();
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.Combine(outDir, name + ".png"));
            Debug.Log("LS_TOUR shot " + name);
            yield return null;
        }
    }
}

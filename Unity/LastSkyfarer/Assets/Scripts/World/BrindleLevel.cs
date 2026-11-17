// The Last Skyfarer: Brindle Isle at runtime. Spawns Kieran and the camera, runs the story director (fades, the
// workshop door, the next morning) and keeps the world in step with the story (the glider, hidden wind, Piko's perch).
// Launch options: -LSContinue (load the autosave), -LSBrindleTour (development screenshot and frame-rate tour).
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LastSkyfarer.World
{
    public class BrindleLevel : MonoBehaviour
    {
        public GameObject KieranPrefab;
        public Transform PlayerStart, InteriorSpawn, DoorSpawn;
        public TimeOfDayDirector TimeOfDay;
        [Tooltip("Small props stop drawing at these distances (layers Cull110 ... Cull650).")]
        public float[] LayerCullDistances = { 110f, 160f, 260f, 450f, 650f };
        public const int FirstCullLayer = 8;

        public StoryManager Story { get; private set; }
        public BrindleStoryDirector Director { get; private set; }
        public KieranController Kieran { get; private set; }
        public ThirdPersonCamera CameraRig { get; private set; }
        public Camera Cam { get; private set; }
        public DevStoryHud Hud { get; private set; }

        public static bool HasArg(string a) => System.Array.Exists(System.Environment.GetCommandLineArgs(), x => x.Equals(a, System.StringComparison.OrdinalIgnoreCase));

        void Awake()
        {
            Story = StoryManager.Instance;
            Story.SceneName = SceneManager.GetActiveScene().name;
            bool resumed = HasArg("-LSContinue") && Story.LoadFromSlot(StoryManager.AutosaveSlot);

            var start = PlayerStart ? PlayerStart : transform;
            Kieran = Instantiate(KieranPrefab).GetComponent<KieranController>();
            Kieran.gameObject.AddComponent<KieranInteractor>();
            Vector3 pos = start.position; float yaw = start.eulerAngles.y;
            if (resumed)
            {
                var d = Core.SaveSystem.Load(StoryManager.AutosaveSlot);
                if (d != null && d.PlayerPosition != Vector3.zero) { pos = d.PlayerPosition; yaw = d.PlayerYaw; }
            }
            Kieran.Teleport(pos, yaw);

            var rig = new GameObject("CameraRig");
            CameraRig = rig.AddComponent<ThirdPersonCamera>();
            CameraRig.Target = Kieran;
            Cam = new GameObject("Camera").AddComponent<Camera>();
            Cam.transform.SetParent(rig.transform, false);
            Cam.tag = "MainCamera";
            Cam.nearClipPlane = 0.1f;
            Cam.farClipPlane = 2600f;
            var cull = new float[32];
            for (int i = 0; i < LayerCullDistances.Length; i++) cull[FirstCullLayer + i] = LayerCullDistances[i];
            Cam.layerCullDistances = cull;
            Cam.layerCullSpherical = true;
            Cam.gameObject.AddComponent<AudioListener>();
            CameraRig.Cam = Cam;
            CameraRig.CollisionMask = ~(1 << 2);      // ignore Ignore Raycast (story volumes)

            Hud = gameObject.AddComponent<DevStoryHud>();
            Hud.Level = this;

            Director = new BrindleStoryDirector(Story);
            Director.OnTeleport += where =>
            {
                var t = where == BrindleStoryDirector.InteriorSpawn ? InteriorSpawn : DoorSpawn;
                if (t) { Kieran.Teleport(t.position, t.eulerAngles.y); CameraRig.Yaw = t.eulerAngles.y; }
            };
            Director.OnFadeOut += s => Hud.FadeTo(1f, s);
            Director.OnFadeIn += s => Hud.FadeTo(0f, s);
            Director.OnApplyStoryState += ApplyStoryState;
            Director.OnMusicCue += cue => Debug.Log("LS_MUSIC cue " + cue + " (music arrives in U5)");
            Director.OnDemoEnd += () => Debug.Log("LS_STORY demo end");
            Story.PlayerPose = () => (Kieran.transform.position, Kieran.transform.eulerAngles.y);
            Story.OnFlagChanged += (f, s) => { if (f == "has_glider" || f == "compass_active" || f == BrindleStoryDirector.RevealedWindFlag) ApplyStoryState(); };

            if (HasArg("-LSBrindleTour")) gameObject.AddComponent<LastSkyfarer.Dev.BrindleTour>().Level = this;
        }

        void Start()
        {
            ApplyStoryState();
            if (TimeOfDay) TimeOfDay.Apply(Story.TimeOfDay, true);
        }

        void OnDestroy() => Director?.Dispose();

        public void ApplyStoryState()
        {
            if (Kieran) Kieran.HasGlider = Story.HasFlag("has_glider");
            foreach (var w in WindVolume.All)
            {
                if ((w.ImpossibleRoute && Story.HasFlag("compass_active")) || (!string.IsNullOrEmpty(w.RevealFlag) && Story.HasFlag(w.RevealFlag))) w.Reveal();
            }
        }

        void Update()
        {
            Director.Tick(Time.deltaTime);
            Story.PlaytimeSeconds += Time.deltaTime;
        }
    }
}

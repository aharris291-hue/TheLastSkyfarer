// The Last Skyfarer: time-of-day lighting (port of ALSTimeOfDayDirector, values from the STYLE_GUIDE Act I colour
// script). One directional light plays the sun by day and the moon at night, so Low keeps a single shadowed light.
// Blends over a few seconds when the story changes the time; a loaded save snaps straight to it.
using System;
using LastSkyfarer.Story;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace LastSkyfarer.World
{
    [Serializable]
    public struct TimeOfDayPreset
    {
        public Vector2 SunPitchYaw;       // degrees below the horizon the light points, compass yaw (0 = north)
        public Color SunColor;
        public float SunIntensity;
        public Color SkyTop, SkyHorizon, SkyBottom, SunGlow;
        public float Stars;
        public Color AmbientSky, AmbientEquator, AmbientGround;
        public Color FogColor;
        public float FogStart, FogEnd;
        public float LampGlow;            // lantern emission, 0 by day
        public Color CloudLit, CloudShade;
        public float CloudCover;
        public Color Grade;               // colour filter for the post-processing grade
        public float Exposure;

        public static TimeOfDayPreset Lerp(TimeOfDayPreset a, TimeOfDayPreset b, float t) => new TimeOfDayPreset
        {
            SunPitchYaw = new Vector2(Mathf.Lerp(a.SunPitchYaw.x, b.SunPitchYaw.x, t), Mathf.LerpAngle(a.SunPitchYaw.y, b.SunPitchYaw.y, t)),
            SunColor = Color.Lerp(a.SunColor, b.SunColor, t), SunIntensity = Mathf.Lerp(a.SunIntensity, b.SunIntensity, t),
            SkyTop = Color.Lerp(a.SkyTop, b.SkyTop, t), SkyHorizon = Color.Lerp(a.SkyHorizon, b.SkyHorizon, t),
            SkyBottom = Color.Lerp(a.SkyBottom, b.SkyBottom, t), SunGlow = Color.Lerp(a.SunGlow, b.SunGlow, t), Stars = Mathf.Lerp(a.Stars, b.Stars, t),
            AmbientSky = Color.Lerp(a.AmbientSky, b.AmbientSky, t), AmbientEquator = Color.Lerp(a.AmbientEquator, b.AmbientEquator, t),
            AmbientGround = Color.Lerp(a.AmbientGround, b.AmbientGround, t), FogColor = Color.Lerp(a.FogColor, b.FogColor, t),
            FogStart = Mathf.Lerp(a.FogStart, b.FogStart, t), FogEnd = Mathf.Lerp(a.FogEnd, b.FogEnd, t), LampGlow = Mathf.Lerp(a.LampGlow, b.LampGlow, t),
            CloudLit = Color.Lerp(a.CloudLit, b.CloudLit, t), CloudShade = Color.Lerp(a.CloudShade, b.CloudShade, t), CloudCover = Mathf.Lerp(a.CloudCover, b.CloudCover, t),
            Grade = Color.Lerp(a.Grade, b.Grade, t), Exposure = Mathf.Lerp(a.Exposure, b.Exposure, t),
        };
    }

    public class TimeOfDayDirector : MonoBehaviour
    {
        public Light Sun;
        public Material Sky;
        [Tooltip("Lantern materials that glow at night.")] public Material[] LampMaterials = new Material[0];
        [Tooltip("Lights that only shine at night (lanterns).")] public Light[] NightLights = new Light[0];
        public float BlendSeconds = 3f;
        [Tooltip("The scene's post-processing profile; its colour adjustments follow the time of day.")] public VolumeProfile Grade;

        public string Current { get; private set; } = "";
        TimeOfDayPreset from, to, now;
        float blend = 1f;
        static readonly int SunDirId = Shader.PropertyToID("_LS_SunDir");

        static Color Hex(string h) => ColorUtility.TryParseHtmlString(h, out var c) ? c : Color.magenta;

        public static TimeOfDayPreset Preset(string tod)
        {
            switch (tod)
            {
                case "Dawn":
                    return new TimeOfDayPreset { SunPitchYaw = new Vector2(12f, 85f), SunColor = new Color(1f, 0.78f, 0.62f), SunIntensity = 0.75f,
                        SkyTop = Hex("#6F86C4"), SkyHorizon = Hex("#F2B9A0"), SkyBottom = Hex("#C7B3DA"), SunGlow = Hex("#FFC48F"),
                        AmbientSky = Hex("#8C8FC0"), AmbientEquator = Hex("#C7A0A8"), AmbientGround = Hex("#5E5468"),
                        FogColor = Hex("#C9AEC9"), FogStart = 80f, FogEnd = 1100f,
                        CloudLit = Hex("#FFD9C2"), CloudShade = Hex("#9C8FB8"), CloudCover = 0.5f, Grade = Hex("#FFF0F0"), Exposure = 0.1f };
                case "Sunset":
                    return new TimeOfDayPreset { SunPitchYaw = new Vector2(6f, 250f), SunColor = new Color(1f, 0.56f, 0.28f), SunIntensity = 1.0f,
                        SkyTop = Hex("#4E5E9E"), SkyHorizon = Hex("#F59A5B"), SkyBottom = Hex("#B98AA6"), SunGlow = Hex("#FF8A3C"),
                        AmbientSky = Hex("#7C78A8"), AmbientEquator = Hex("#D08868"), AmbientGround = Hex("#5A4450"),
                        FogColor = Hex("#E7926A"), FogStart = 100f, FogEnd = 1200f,
                        CloudLit = Hex("#FFB27A"), CloudShade = Hex("#8A6E99"), CloudCover = 0.55f, Grade = Hex("#FFEBDD"), Exposure = 0.05f };
                case "Night":
                    // The moon (STYLE_GUIDE: cool blue, never pitch black).
                    return new TimeOfDayPreset { SunPitchYaw = new Vector2(40f, 200f), SunColor = new Color(0.55f, 0.66f, 1f), SunIntensity = 0.32f,
                        SkyTop = Hex("#0B1230"), SkyHorizon = Hex("#26345E"), SkyBottom = Hex("#1A2040"), SunGlow = Hex("#8FA6E0"), Stars = 0.9f,
                        AmbientSky = Hex("#2E3C6E"), AmbientEquator = Hex("#28304E"), AmbientGround = Hex("#141828"),
                        FogColor = Hex("#141C36"), FogStart = 60f, FogEnd = 900f, LampGlow = 1f,
                        CloudLit = Hex("#5A6A9C"), CloudShade = Hex("#1C2444"), CloudCover = 0.35f, Grade = Hex("#DDE6FF"), Exposure = 0.35f };
                default:    // Morning (and Noon)
                    return new TimeOfDayPreset { SunPitchYaw = new Vector2(tod == "Noon" ? 60f : 28f, 60f), SunColor = new Color(1f, 0.93f, 0.82f), SunIntensity = 1.3f,
                        SkyTop = Hex("#4F8FDB"), SkyHorizon = Hex("#CFE3F4"), SkyBottom = Hex("#BFB8DC"), SunGlow = Hex("#FFF1CF"),
                        AmbientSky = Hex("#9DB8DE"), AmbientEquator = Hex("#B9B9A6"), AmbientGround = Hex("#5D6448"),
                        FogColor = Hex("#A9C2E3"), FogStart = 150f, FogEnd = 1600f,
                        CloudLit = Hex("#FFFFFF"), CloudShade = Hex("#B4C0DC"), CloudCover = 0.42f, Grade = Hex("#FFFFFF"), Exposure = 0f };
            }
        }

        void OnEnable()
        {
            StoryManager.Instance.OnTimeOfDayChanged += OnStoryTime;
            Apply(StoryManager.Instance.TimeOfDay, true);
        }

        void OnDisable() => StoryManager.Instance.OnTimeOfDayChanged -= OnStoryTime;

        void OnStoryTime(string tod) => Apply(tod, false);

        public void Apply(string tod, bool snap)
        {
            Current = tod;
            from = now;
            to = Preset(tod);
            if (snap || BlendSeconds <= 0f) { blend = 1f; Set(to); }
            else blend = 0f;
        }

        void Update()
        {
            if (blend >= 1f) return;
            blend = Mathf.Min(1f, blend + Time.deltaTime / BlendSeconds);
            Set(TimeOfDayPreset.Lerp(from, to, Mathf.SmoothStep(0f, 1f, blend)));
        }

        void Set(TimeOfDayPreset p)
        {
            now = p;
            if (Sun)
            {
                Sun.transform.rotation = Quaternion.Euler(p.SunPitchYaw.x, p.SunPitchYaw.y, 0f);
                Sun.color = p.SunColor;
                Sun.intensity = p.SunIntensity;
                Shader.SetGlobalVector(SunDirId, -Sun.transform.forward);
                RenderSettings.sun = Sun;
            }
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = p.AmbientSky;
            RenderSettings.ambientEquatorColor = p.AmbientEquator;
            RenderSettings.ambientGroundColor = p.AmbientGround;
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = p.FogColor;
            RenderSettings.fogStartDistance = p.FogStart;
            RenderSettings.fogEndDistance = p.FogEnd;
            if (Sky)
            {
                Sky.SetColor("_TopColor", p.SkyTop);
                Sky.SetColor("_HorizonColor", p.SkyHorizon);
                Sky.SetColor("_BottomColor", p.SkyBottom);
                Sky.SetColor("_SunColor", p.SunGlow);
                Sky.SetFloat("_Stars", p.Stars);
                Sky.SetColor("_CloudLit", p.CloudLit);
                Sky.SetColor("_CloudShade", p.CloudShade);
                Sky.SetFloat("_CloudCover", p.CloudCover);
                RenderSettings.skybox = Sky;
            }
            if (Grade)
            {
                if (Grade.TryGet(out ColorAdjustments ca)) { ca.colorFilter.Override(p.Grade); ca.postExposure.Override(p.Exposure); }
            }
            foreach (var m in LampMaterials) if (m) m.SetColor("_Emission", new Color(1f, 0.68f, 0.38f) * (1.6f * p.LampGlow));
            foreach (var l in NightLights) if (l) { l.enabled = p.LampGlow > 0.05f; l.intensity = 2.5f * p.LampGlow; }
        }
    }
}

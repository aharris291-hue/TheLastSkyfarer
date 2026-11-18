// The Last Skyfarer: player settings (ported from the Unreal ULSSettings). Saved per user as JSON. On first launch the
// graphics preset is detected: Low on integrated graphics (e.g. Intel UHD 630) with 70% render scale and a 30 fps cap.
using System;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace LastSkyfarer.Core
{
    [Serializable]
    public class GameSettings
    {
        [Range(0f, 1f)] public float MasterVolume = 1f;
        [Range(0f, 1f)] public float MusicVolume = 0.8f;
        [Range(0f, 1f)] public float EffectsVolume = 1f;
        public float LookSensitivity = 1f;
        public bool InvertY;
        public bool Subtitles = true;
        public string Quality = "";          // "" = not chosen yet (detected on first launch)
        [Range(50, 100)] public int ResolutionScale = 100;
        public bool VSync;
        public int FrameCap = 60;            // 0 = unlimited

        static GameSettings current;
        public static event Action Changed;
        public static string FilePath => Path.Combine(Application.persistentDataPath, "settings.json");

        public static GameSettings Current
        {
            get
            {
                if (current != null) return current;
                try { current = File.Exists(FilePath) ? JsonUtility.FromJson<GameSettings>(File.ReadAllText(FilePath)) : null; }
                catch { current = null; }
                current ??= new GameSettings();
                return current;
            }
        }

        public static bool IsIntegratedGpu(string deviceName, int vendorId)
        {
            string n = deviceName ?? "";
            return (vendorId == 0x8086 && !n.Contains("Arc")) || n.Contains("UHD Graphics") || n.Contains("HD Graphics") || n.Contains("Iris");
        }

        public static string DetectQuality()
        {
            bool integrated = IsIntegratedGpu(SystemInfo.graphicsDeviceName, SystemInfo.graphicsDeviceVendorID);
            string q = integrated || SystemInfo.graphicsMemorySize < 1500 ? "Low" : "PC";
            Debug.Log($"LS_SETTINGS detected {q} for '{SystemInfo.graphicsDeviceName}' (integrated {integrated})");
            return q;
        }

        public void Save()
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(FilePath));
                File.WriteAllText(FilePath, JsonUtility.ToJson(this, true));
            }
            catch (Exception e) { Debug.LogError("LS_SETTINGS save failed: " + e.Message); }
        }

        /// <summary>Applies everything. -LSQuality=Low|Mobile|PC overrides the preset for this run (not saved).</summary>
        public void Apply()
        {
            if (string.IsNullOrEmpty(Quality))
            {
                Quality = DetectQuality();
                if (Quality == "Low") { ResolutionScale = 70; FrameCap = 30; }
                Save();
            }
            string q = Quality;
            foreach (string arg in Environment.GetCommandLineArgs())
                if (arg.StartsWith("-LSQuality=")) q = arg.Substring("-LSQuality=".Length);
            int level = Array.IndexOf(QualitySettings.names, q);
            if (level >= 0) QualitySettings.SetQualityLevel(level, true);
            if (!Application.isEditor && QualitySettings.renderPipeline is UniversalRenderPipelineAsset urp) urp.renderScale = Mathf.Clamp(ResolutionScale, 50, 100) / 100f;
            QualitySettings.vSyncCount = VSync ? 1 : 0;
            Application.targetFrameRate = FrameCap > 0 ? FrameCap : -1;
            AudioListener.volume = Mathf.Clamp01(MasterVolume);
            Changed?.Invoke();
            Debug.Log($"LS_SETTINGS graphics {QualitySettings.names[QualitySettings.GetQualityLevel()]}, {ResolutionScale}% resolution, vsync {VSync}, cap {FrameCap}");
        }

        public void SaveAndApply() { Save(); Apply(); }
    }
}

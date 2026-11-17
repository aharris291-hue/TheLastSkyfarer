// The Last Skyfarer: runs once before the first scene. Caps the frame rate (30 on Low, as on Adam's UHD 630).
using UnityEngine;

namespace LastSkyfarer.Core
{
    public static class GameBootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Init()
        {
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = QualitySettings.names[QualitySettings.GetQualityLevel()] == "Low" ? 30 : 60;
        }
    }
}

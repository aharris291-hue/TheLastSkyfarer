// The Last Skyfarer: runs once before the first scene. Applies the player's settings (first launch detects the
// graphics preset: Low with a 30 fps cap on integrated graphics like Adam's UHD 630).
using UnityEngine;

namespace LastSkyfarer.Core
{
    public static class GameBootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Init()
        {
            GameSettings.Current.Apply();
        }
    }
}

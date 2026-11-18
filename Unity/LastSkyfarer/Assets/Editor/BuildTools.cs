// The Last Skyfarer: batchmode builds.
//   Unity.exe -batchmode -projectPath <project> -executeMethod LastSkyfarer.EditorTools.BuildTools.BuildShowcase -quit
using LastSkyfarer.Dev;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace LastSkyfarer.EditorTools
{
    public static class BuildTools
    {
        public const string ShowcaseScene = "Assets/Scenes/Dev/KieranShowcase.unity";

        [MenuItem("Last Skyfarer/Build Kieran Showcase")]
        public static void BuildShowcase()
        {
            System.IO.Directory.CreateDirectory("Assets/Scenes/Dev");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var go = new GameObject("Showcase");
            go.AddComponent<KieranShowcase>().KieranPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Kieran.prefab");
            EditorSceneManager.SaveScene(scene, ShowcaseScene);
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ShowcaseScene },
                locationPathName = "../Builds/KieranShowcase/LastSkyfarer.exe",
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            });
            Debug.Log($"LS_BUILD showcase {report.summary.result}, {report.summary.totalSize / (1024 * 1024)} MB, {report.summary.totalErrors} errors");
        }
    }
}

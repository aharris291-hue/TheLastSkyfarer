// The Last Skyfarer (Unity): one-off project setup, run in batchmode.
//   Unity.exe -batchmode -projectPath <project> -executeMethod LastSkyfarer.EditorTools.ProjectSetup.Run -quit
// Text serialization, visible meta files, and a "Low" URP quality level for Intel UHD 630 class GPUs, set as default.
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace LastSkyfarer.EditorTools
{
    public static class ProjectSetup
    {
        const string LowAssetPath = "Assets/Settings/Low_RPAsset.asset";

        public static void Run()
        {
            EditorSettings.serializationMode = SerializationMode.ForceText;
            VersionControlSettings.mode = "Visible Meta Files";
            PlayerSettings.companyName = "Adam Harris";
            PlayerSettings.productName = "The Last Skyfarer";

            // Low pipeline asset: a copy of the template's mobile asset, tuned for integrated graphics.
            if (AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(LowAssetPath) == null)
            {
                AssetDatabase.CopyAsset("Assets/Settings/Mobile_RPAsset.asset", LowAssetPath);
            }
            var low = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(LowAssetPath);
            low.renderScale = 0.7f;
            low.msaaSampleCount = 1;
            low.shadowCascadeCount = 1;
            low.shadowDistance = 40f;
            low.supportsHDR = false;
            low.supportsCameraDepthTexture = false;
            low.supportsCameraOpaqueTexture = false;
            EditorUtility.SetDirty(low);

            // Insert "Low" as quality level 0 and make it the default on every platform.
            var qs = new SerializedObject(AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/QualitySettings.asset")[0]);
            var levels = qs.FindProperty("m_QualitySettings");
            int lowIndex = -1;
            for (int i = 0; i < levels.arraySize; i++)
            {
                if (levels.GetArrayElementAtIndex(i).FindPropertyRelative("name").stringValue == "Low") lowIndex = i;
            }
            if (lowIndex < 0)
            {
                levels.InsertArrayElementAtIndex(0);   // copies element 0, then we rename and retune it
                lowIndex = 0;
            }
            var lv = levels.GetArrayElementAtIndex(lowIndex);
            lv.FindPropertyRelative("name").stringValue = "Low";
            lv.FindPropertyRelative("excludedTargetPlatforms").ClearArray();   // the copied mobile level excluded desktop builds
            lv.FindPropertyRelative("customRenderPipeline").objectReferenceValue = low;
            lv.FindPropertyRelative("vSyncCount").intValue = 0;          // the game caps at 30 fps itself
            lv.FindPropertyRelative("antiAliasing").intValue = 0;
            lv.FindPropertyRelative("anisotropicTextures").intValue = 0;
            lv.FindPropertyRelative("lodBias").floatValue = 0.7f;
            lv.FindPropertyRelative("globalTextureMipmapLimit").intValue = 0;
            qs.FindProperty("m_CurrentQuality").intValue = lowIndex;
            var perPlatform = qs.FindProperty("m_PerPlatformDefaultQuality");
            for (int i = 0; i < perPlatform.arraySize; i++)
            {
                perPlatform.GetArrayElementAtIndex(i).FindPropertyRelative("second").intValue = lowIndex;
            }
            qs.ApplyModifiedPropertiesWithoutUndo();
            QualitySettings.SetQualityLevel(lowIndex, true);

            AssetDatabase.SaveAssets();
            Debug.Log("LS_SETUP_OK quality levels: " + string.Join(", ", QualitySettings.names) + " (default " + QualitySettings.names[lowIndex] + ")");
        }
    }
}

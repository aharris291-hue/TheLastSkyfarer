// The Last Skyfarer: rendering quality for the polish pass. Low gets its own renderer with screen-space ambient
// occlusion (downsampled, few samples), HDR for bloom, and two shadow cascades out to 70 m; PC gets more of each.
// Also makes the post-processing profile (tonemapping, a painterly grade, soft bloom, vignette). Measured on the
// UHD 630: the island renders at several hundred fps uncapped on Low before this pass, so there is room for it.
//   Unity.exe -batchmode -projectPath <project> -executeMethod LastSkyfarer.EditorTools.RenderingSetup.Run -quit
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace LastSkyfarer.EditorTools
{
    public static class RenderingSetup
    {
        const string LowAsset = "Assets/Settings/Low_RPAsset.asset";
        const string PcAsset = "Assets/Settings/PC_RPAsset.asset";
        const string LowRenderer = "Assets/Settings/Low_Renderer.asset";
        const string PcRenderer = "Assets/Settings/PC_Renderer.asset";
        public const string PostProfile = "Assets/Art/Brindle/BrindlePost.asset";

        public static void Run()
        {
            if (!AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(LowRenderer))
                AssetDatabase.CopyAsset("Assets/Settings/Mobile_Renderer.asset", LowRenderer);
            var lowRenderer = AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(LowRenderer);
            var pcRenderer = AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(PcRenderer);
            EnsureSsao(lowRenderer, intensity: 1.1f, radius: 0.45f, samplesLow: true);
            EnsureSsao(pcRenderer, intensity: 1.2f, radius: 0.5f, samplesLow: false);

            var low = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(LowAsset);
            var so = new SerializedObject(low);
            var list = so.FindProperty("m_RendererDataList");
            list.arraySize = 1;
            list.GetArrayElementAtIndex(0).objectReferenceValue = lowRenderer;
            so.FindProperty("m_DefaultRendererIndex").intValue = 0;
            so.ApplyModifiedPropertiesWithoutUndo();
            low.supportsHDR = true;
            low.shadowDistance = 70f;
            low.shadowCascadeCount = 2;
            low.mainLightShadowmapResolution = 2048;
            EditorUtility.SetDirty(low);

            var pc = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(PcAsset);
            pc.supportsHDR = true;
            pc.shadowDistance = 120f;
            pc.shadowCascadeCount = 4;
            EditorUtility.SetDirty(pc);

            MakePostProfile();
            AssetDatabase.SaveAssets();
            Debug.Log($"LS_RENDERING Low renderer features: {string.Join(", ", lowRenderer.rendererFeatures.Select(f => f ? f.name : "null"))}; PC: {string.Join(", ", pcRenderer.rendererFeatures.Select(f => f ? f.name : "null"))}");
        }

        static void EnsureSsao(ScriptableRendererData data, float intensity, float radius, bool samplesLow)
        {
            var ssao = data.rendererFeatures.OfType<ScreenSpaceAmbientOcclusion>().FirstOrDefault();
            if (!ssao)
            {
                ssao = ScriptableObject.CreateInstance<ScreenSpaceAmbientOcclusion>();
                ssao.name = "ScreenSpaceAmbientOcclusion";
                AssetDatabase.AddObjectToAsset(ssao, data);
                AssetDatabase.TryGetGUIDAndLocalFileIdentifier(ssao, out string _, out long id);
                var dso = new SerializedObject(data);
                var features = dso.FindProperty("m_RendererFeatures");
                features.arraySize++;
                features.GetArrayElementAtIndex(features.arraySize - 1).objectReferenceValue = ssao;
                var map = dso.FindProperty("m_RendererFeatureMap");
                map.arraySize++;
                map.GetArrayElementAtIndex(map.arraySize - 1).longValue = id;
                dso.ApplyModifiedPropertiesWithoutUndo();
            }
            var s = new SerializedObject(ssao).FindProperty("m_Settings");
            void Set(string name, System.Action<SerializedProperty> f) { var p = s.FindPropertyRelative(name); if (p != null) f(p); else Debug.LogWarning("LS_RENDERING no SSAO setting " + name); }
            Set("Downsample", p => p.boolValue = true);
            Set("AfterOpaque", p => p.boolValue = false);
            Set("Intensity", p => p.floatValue = intensity);
            Set("DirectLightingStrength", p => p.floatValue = 0.2f);
            Set("Radius", p => p.floatValue = radius);
            Set("Samples", p => p.enumValueIndex = samplesLow ? 2 : 1);   // Low / Medium
            Set("Source", p => p.enumValueIndex = 1);                      // depth and normals (our shaders write them)
            // Character fidelity pass: smooth, low-noise occlusion. The blue-noise pattern at Low samples left blotches on
            // skin and cloth once the characters moved to URP Lit; interleaved gradient noise with the bilateral blur
            // gives the same contact shading without the mottling.
            Set("AOMethod", p => p.enumValueIndex = 1);                     // InterleavedGradient
            Set("BlurQuality", p => p.enumValueIndex = 0);                  // High (bilateral)
            s.serializedObject.ApplyModifiedPropertiesWithoutUndo();
            ssao.SetActive(true);
            EditorUtility.SetDirty(ssao);
            EditorUtility.SetDirty(data);
        }

        static void MakePostProfile()
        {
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(PostProfile);
            if (!profile)
            {
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, PostProfile);
            }
            T Get<T>() where T : VolumeComponent
            {
                if (!profile.TryGet(out T c)) { c = profile.Add<T>(true); c.name = typeof(T).Name; AssetDatabase.AddObjectToAsset(c, profile); }
                c.active = true;
                return c;
            }
            var tone = Get<Tonemapping>();
            tone.mode.Override(TonemappingMode.Neutral);
            var ca = Get<ColorAdjustments>();
            ca.contrast.Override(10f);
            ca.saturation.Override(14f);
            ca.postExposure.Override(0f);
            ca.colorFilter.Override(Color.white);
            // Painterly split tone: cool violet shadows, warm highlights (STYLE_GUIDE colour script).
            var smh = Get<ShadowsMidtonesHighlights>();
            smh.shadows.Override(new Vector4(0.93f, 0.93f, 1.06f, -0.02f));
            smh.highlights.Override(new Vector4(1.04f, 1.0f, 0.95f, 0.02f));
            var bloom = Get<Bloom>();
            bloom.threshold.Override(0.95f);
            bloom.intensity.Override(0.45f);
            bloom.scatter.Override(0.68f);
            bloom.tint.Override(new Color(1f, 0.92f, 0.82f));
            bloom.highQualityFiltering.Override(false);
            bloom.downscale.Override(BloomDownscaleMode.Quarter);
            var vig = Get<Vignette>();
            vig.intensity.Override(0.22f);
            vig.smoothness.Override(0.45f);
            EditorUtility.SetDirty(profile);
        }
    }
}

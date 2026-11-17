// The Last Skyfarer: stylised character shading (polish pass 1), for Kieran and the villagers. Painted base colour
// with a soft, warm light ramp (skin and cloth read like a painting, not plastic), a gentle subsurface warmth on the
// shadow side, a rim of sky light that lifts the silhouette off the background, a soft highlight on metal and leather
// (metallic slot), screen-space ambient occlusion and real shadows. Skinned meshes, one texture.
Shader "LastSkyfarer/StylisedCharacter"
{
    Properties
    {
        _BaseMap ("Base colour", 2D) = "white" {}
        _BaseColor ("Tint", Color) = (1, 1, 1, 1)
        _ShadowTint ("Shadow tint", Color) = (0.86, 0.76, 0.82, 1)
        _Warmth ("Shadow-side warmth", Range(0, 1)) = 0.35
        _RampSoftness ("Light ramp softness", Range(0.02, 1)) = 0.35
        _Rim ("Rim light", Range(0, 2)) = 0.6
        _RimPower ("Rim tightness", Range(1, 8)) = 3.5
        _Specular ("Highlight", Range(0, 2)) = 0.15
        _Gloss ("Highlight tightness", Range(2, 256)) = 24
        _Metallic ("Metal (brass, buckles)", Range(0, 1)) = 0
        _Ambient ("Ambient fill", Range(0.5, 2)) = 1.35
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _BaseMap_ST;
            half4 _BaseColor, _ShadowTint;
            half _Warmth, _RampSoftness, _Rim, _RimPower, _Specular, _Gloss, _Metallic, _Ambient;
        CBUFFER_END
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; half3 normalWS : TEXCOORD1; float2 uv : TEXCOORD2; half fog : TEXCOORD3; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(i.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.uv = TRANSFORM_TEX(i.uv, _BaseMap);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings i) : SV_Target
            {
                half3 albedo = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb * _BaseColor.rgb;
                half3 n = normalize(i.normalWS);
                half3 v = SafeNormalize(GetWorldSpaceViewDir(i.positionWS));
                Light sun = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                #if defined(_SCREEN_SPACE_OCCLUSION)
                    AmbientOcclusionFactor ssao = GetScreenSpaceAmbientOcclusion(GetNormalizedScreenSpaceUV(i.positionCS));
                    half aoI = ssao.indirectAmbientOcclusion, aoD = ssao.directAmbientOcclusion;
                #else
                    half aoI = 1.0, aoD = 1.0;
                #endif
                half ndl = dot(n, sun.direction);
                half shadow = sun.shadowAttenuation * sun.distanceAttenuation * aoD;
                half ramp = smoothstep(-_RampSoftness * 0.5, _RampSoftness, ndl) * shadow;
                // Shadow side: tinted, with a little warmth bleeding through (skin, cloth).
                half3 shade = lerp(_ShadowTint.rgb, half3(1.0, 0.82, 0.72), _Warmth * saturate(1.0 - abs(ndl)));
                half3 ambient = SampleSH(n) * aoI * _Ambient;
                half3 lit = albedo * (sun.color * ramp + ambient * lerp(shade, 1.0, ramp));
                #if defined(_ADDITIONAL_LIGHTS)
                    uint count = GetAdditionalLightsCount();
                    LIGHT_LOOP_BEGIN(count)
                        Light l = GetAdditionalLight(lightIndex, i.positionWS);
                        lit += albedo * l.color * (smoothstep(0.0, 0.5, dot(n, l.direction)) * l.distanceAttenuation * l.shadowAttenuation);
                    LIGHT_LOOP_END
                #endif
                half3 h = SafeNormalize(sun.direction + v);
                half spec = pow(saturate(dot(n, h)), lerp(_Gloss, _Gloss * 3.0, _Metallic)) * lerp(_Specular, 1.2, _Metallic) * shadow;
                lit += lerp(sun.color, sun.color * albedo * 2.0, _Metallic) * spec;
                half rim = pow(1.0 - saturate(dot(n, v)), _RimPower) * _Rim;
                lit += (SampleSH(half3(0, 1, 0)) * 0.7 + sun.color * 0.35 * saturate(dot(-v, sun.direction) + 0.4)) * rim * aoI;
                return half4(MixFog(lit, i.fog), 1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            float3 _LightDirection;
            float3 _LightPosition;
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            float4 Vert(Attributes i) : SV_POSITION
            {
                float3 ws = TransformObjectToWorld(i.positionOS.xyz);
                #if _CASTING_PUNCTUAL_LIGHT_SHADOW
                    float3 dir = normalize(_LightPosition - ws);
                #else
                    float3 dir = _LightDirection;
                #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(ws, TransformObjectToWorldNormal(i.normalOS), dir));
                #if UNITY_REVERSED_Z
                    cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
                #else
                    cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
                #endif
                return cs;
            }
            half4 Frag() : SV_Target { return 0; }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            float4 Vert(float4 positionOS : POSITION) : SV_POSITION { return TransformObjectToHClip(positionOS.xyz); }
            half4 Frag() : SV_Target { return 0; }
            ENDHLSL
        }
        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; half3 normalWS : TEXCOORD0; };
            Varyings Vert(Attributes i) { Varyings o; o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.normalWS = TransformObjectToWorldNormal(i.normalOS); return o; }
            half4 Frag(Varyings i) : SV_Target { return half4(NormalizeNormalPerPixel(i.normalWS), 0.0); }
            ENDHLSL
        }
    }
    FallBack Off
}

// The Last Skyfarer: hair cards (character pass). Alpha-cut strand cards grown from each character's hair, lit with
// two Kajiya-Kay highlights along the real strand direction (the card's tangent), darker at the root, coloured per
// card from the character's painted hair, two-sided, casting proper cut-out shadows.
Shader "LastSkyfarer/HairCards"
{
    Properties
    {
        _StrandMap ("Strands (alpha cut-out, grey shade)", 2D) = "white" {}
        _Cutoff ("Cut-off", Range(0, 1)) = 0.45
        _Shine ("Primary highlight", Range(0, 2)) = 0.3
        _Shine2 ("Tinted highlight", Range(0, 2)) = 0.55
        _Shift ("Highlight shift", Range(-1, 1)) = 0.12
        _RootDark ("Root darkening", Range(0, 1)) = 0.25
    }
    SubShader
    {
        Tags { "RenderType" = "TransparentCutout" "Queue" = "AlphaTest" "RenderPipeline" = "UniversalPipeline" }
        Cull Off
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _StrandMap_ST;
            half _Cutoff, _Shine, _Shine2, _Shift, _RootDark;
        CBUFFER_END
        TEXTURE2D(_StrandMap); SAMPLER(sampler_StrandMap);
        ENDHLSL
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 tangentOS : TANGENT; float2 uv : TEXCOORD0; half4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; half3 normalWS : TEXCOORD1; half3 tangentWS : TEXCOORD2; float2 uv : TEXCOORD3; half4 color : COLOR; half fog : TEXCOORD4; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(i.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.tangentWS = TransformObjectToWorldDir(i.tangentOS.xyz);
                o.uv = i.uv;
                o.color = i.color;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings i, bool front : SV_IsFrontFace) : SV_Target
            {
                half4 s = SAMPLE_TEXTURE2D(_StrandMap, sampler_StrandMap, i.uv);
                clip(s.a - _Cutoff);
                half3 n = normalize(i.normalWS) * (front ? 1 : -1);
                half3 t = normalize(i.tangentWS);
                half3 v = SafeNormalize(GetWorldSpaceViewDir(i.positionWS));
                Light sun = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                half3 albedo = i.color.rgb * (0.88 + 0.2 * s.r) * lerp(1.0 - _RootDark, 1.0, saturate(i.uv.y * 1.6));   // gentle: light hair must not turn grey
                half ndl = saturate(abs(dot(n, sun.direction)) * 0.6 + 0.4);   // thin cards: lit through from either side
                half shadow = lerp(0.55, 1.0, sun.shadowAttenuation);   // soft: thin strands let light through
                half3 lit = albedo * (sun.color * ndl * shadow + SampleSH(normalize(n * 0.3 + half3(0, 1, 0))) * 1.2);   // sky fill, never the dark ground
                half3 h = SafeNormalize(sun.direction + v);
                half3 t1 = normalize(t + n * (_Shift + (s.r - 0.5) * 0.3));
                half3 t2 = normalize(t + n * (_Shift - 0.35 + (s.r - 0.5) * 0.3));
                half d1 = dot(t1, h), d2 = dot(t2, h);
                half spec1 = pow(saturate(sqrt(1.0 - d1 * d1)), 120.0) * _Shine;
                half spec2 = pow(saturate(sqrt(1.0 - d2 * d2)), 30.0) * _Shine2;
                lit += sun.color * (spec1 * lerp(albedo, 1.0, 0.35) + spec2 * albedo) * shadow * saturate(dot(n, sun.direction) + 0.5);   // tinted: no white shards on dark hair
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
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            float3 _LightDirection;
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                float3 ws = TransformObjectToWorld(i.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(ApplyShadowBias(ws, TransformObjectToWorldNormal(i.normalOS), _LightDirection));
                #if UNITY_REVERSED_Z
                    o.positionCS.z = min(o.positionCS.z, UNITY_NEAR_CLIP_VALUE);
                #else
                    o.positionCS.z = max(o.positionCS.z, UNITY_NEAR_CLIP_VALUE);
                #endif
                o.uv = i.uv;
                return o;
            }
            half4 Frag(Varyings i) : SV_Target { clip(SAMPLE_TEXTURE2D(_StrandMap, sampler_StrandMap, i.uv).a - _Cutoff); return 0; }
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
            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
            Varyings Vert(Attributes i) { Varyings o; o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.uv = i.uv; return o; }
            half4 Frag(Varyings i) : SV_Target { clip(SAMPLE_TEXTURE2D(_StrandMap, sampler_StrandMap, i.uv).a - _Cutoff); return 0; }
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
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; half3 normalWS : TEXCOORD0; float2 uv : TEXCOORD1; };
            Varyings Vert(Attributes i) { Varyings o; o.positionCS = TransformObjectToHClip(i.positionOS.xyz); o.normalWS = TransformObjectToWorldNormal(i.normalOS); o.uv = i.uv; return o; }
            half4 Frag(Varyings i) : SV_Target { clip(SAMPLE_TEXTURE2D(_StrandMap, sampler_StrandMap, i.uv).a - _Cutoff); return half4(NormalizeNormalPerPixel(i.normalWS), 0.0); }
            ENDHLSL
        }
    }
    FallBack Off
}

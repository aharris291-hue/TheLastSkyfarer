// The Last Skyfarer: the cloud sea and the cloud puffs under the island (port of M_CloudSea). Slowly drifting lilac and
// white cloud tops from two scrolling brush-noise samples, lit by the sun with a soft glow so they never go grey.
Shader "LastSkyfarer/CloudSea"
{
    Properties
    {
        _BrushNoise ("Brush noise", 2D) = "gray" {}
        _ShadowColor ("Shadow colour", Color) = (0.73, 0.68, 0.84, 1)
        _LightColor ("Light colour", Color) = (0.98, 0.96, 0.95, 1)
        _CloudScale ("Cloud scale (m)", Float) = 60
        _Drift ("Drift speed (m/s)", Float) = 1.5
        _Glow ("Glow", Range(0, 1)) = 0.35
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry+10" }
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            CBUFFER_START(UnityPerMaterial)
                float4 _BrushNoise_ST;
                half4 _ShadowColor, _LightColor;
                float _CloudScale, _Drift;
                half _Glow;
            CBUFFER_END
            TEXTURE2D(_BrushNoise); SAMPLER(sampler_BrushNoise);
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; half3 normalWS : TEXCOORD1; half fog : TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(i.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings i) : SV_Target
            {
                float2 uv = (i.positionWS.xz + i.positionWS.y * 0.5) / _CloudScale;
                half a = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, uv + _Time.y * _Drift / _CloudScale * float2(1, 0.3)).r;
                half b = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, uv * 0.37 - _Time.y * _Drift / _CloudScale * float2(0.2, 0.7)).g;
                half puff = 0.35 + 0.65 * smoothstep(0.15, 0.95, a * 0.55 + b * 0.55);   // soft, never hard-edged
                half3 col = lerp(_ShadowColor.rgb, _LightColor.rgb, puff);
                Light sun = GetMainLight();
                half3 n = normalize(i.normalWS);
                half3 light = sun.color * saturate(dot(n, sun.direction) * 0.5 + 0.5) + SampleSH(n);
                half3 c = col * lerp(light, max(light, 1.0), _Glow);
                return half4(MixFog(c, i.fog), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

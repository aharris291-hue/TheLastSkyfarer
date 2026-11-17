// The Last Skyfarer: flowing wind ribbons (port of M_WindRibbon). Soft additive streaks that run along the wind line,
// so currents and updrafts can be read from the air. Used on LineRenderers with Tile texture mode (uv.x in metres).
Shader "LastSkyfarer/WindRibbon"
{
    Properties
    {
        _Color ("Colour", Color) = (0.81, 0.94, 1, 1)
        _Intensity ("Intensity", Float) = 1
        _FlowSpeed ("Flow speed (m/s)", Float) = 6
        _StreakLength ("Streak spacing (m)", Float) = 7
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" }
        Blend One One
        ZWrite Off
        Cull Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                float _Intensity, _FlowSpeed, _StreakLength;
            CBUFFER_END
            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; half fog : TEXCOORD1; half near : TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                float3 ws = TransformObjectToWorld(i.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(ws);
                o.near = saturate((distance(ws, _WorldSpaceCameraPos) - 4.0) / 14.0);   // no smears right by the camera
                o.uv = i.uv;
                o.color = i.color;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings i) : SV_Target
            {
                float f = frac(i.uv.x / _StreakLength - _Time.y * _FlowSpeed / _StreakLength);
                half streak = smoothstep(0.0, 0.35, f) * (1.0 - smoothstep(0.55, 1.0, f));
                half edge = 1.0 - abs(i.uv.y * 2.0 - 1.0);
                half a = streak * edge * edge * _Intensity * i.color.a * i.near;
                half3 c = _Color.rgb * a;
                return half4(MixFogColor(c, half3(0, 0, 0), i.fog), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

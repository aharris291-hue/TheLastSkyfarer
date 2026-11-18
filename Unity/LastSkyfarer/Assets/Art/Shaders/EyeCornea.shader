// The Last Skyfarer: the wet, clear layer over each eye (character pass): a glossy cornea that reflects the sky at
// grazing angles, the sun's highlight and a soft catchlight that always faces the camera; and, with _Wet = 1, the
// thin moist line along the lower lid. Transparent, drawn over the painted eye.
Shader "LastSkyfarer/EyeCornea"
{
    Properties
    {
        _Tint ("Tint", Color) = (1, 1, 1, 1)
        _Catch ("Catchlight", Range(0, 4)) = 2.2
        _Gloss ("Gloss", Range(50, 1000)) = 420
        _Wet ("Wet line (0 cornea, 1 lid line)", Range(0, 1)) = 0
        _Opacity ("Base opacity", Range(0, 1)) = 0.06
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" }
        Blend One OneMinusSrcAlpha
        ZWrite Off
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
                half4 _Tint;
                half _Catch, _Gloss, _Wet, _Opacity;
            CBUFFER_END
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
                half3 n = normalize(i.normalWS);
                half3 v = SafeNormalize(GetWorldSpaceViewDir(i.positionWS));
                Light sun = GetMainLight();
                half fres = pow(1.0 - saturate(dot(n, v)), 4.0);
                half3 sky = SampleSH(reflect(-v, n)) * fres * 0.8;
                half3 h = SafeNormalize(sun.direction + v);
                half spec = pow(saturate(dot(n, h)), _Gloss) * 2.0;
                half3 camRight = UNITY_MATRIX_V[0].xyz, camUp = UNITY_MATRIX_V[1].xyz;
                half3 hc = SafeNormalize(normalize(v + camUp * 0.5 - camRight * 0.3) + v);
                half catchlight = pow(saturate(dot(n, hc)), _Gloss * 0.8) * _Catch;
                half3 c = sky + sun.color * spec + catchlight;
                half a = saturate(_Opacity + fres * 0.3 + spec + catchlight);
                if (_Wet > 0.5) { c = c * 0.6 + half3(0.95, 0.75, 0.72) * 0.25; a = saturate(0.35 + spec + catchlight * 0.5); }
                c *= _Tint.rgb;
                return half4(MixFog(c, i.fog), a);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

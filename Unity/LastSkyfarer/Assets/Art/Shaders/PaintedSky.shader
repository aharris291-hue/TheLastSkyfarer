// The Last Skyfarer: painted sky (skybox). A three-colour gradient with a soft sun glow and, at night, faint stars.
// The time-of-day director sets the colours and _LS_SunDir every frame while it blends.
Shader "LastSkyfarer/PaintedSky"
{
    Properties
    {
        _TopColor ("Top", Color) = (0.36, 0.6, 0.9, 1)
        _HorizonColor ("Horizon", Color) = (0.8, 0.88, 0.95, 1)
        _BottomColor ("Below", Color) = (0.72, 0.68, 0.84, 1)
        _SunColor ("Sun glow", Color) = (1, 0.92, 0.75, 1)
        _SunSize ("Sun size (1 - cos of the disc radius)", Range(0.00005, 0.01)) = 0.0005
        _Stars ("Stars", Range(0, 1)) = 0
    }
    SubShader
    {
        Tags { "Queue" = "Background" "RenderType" = "Background" "PreviewType" = "Skybox" "RenderPipeline" = "UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            CBUFFER_START(UnityPerMaterial)
                half4 _TopColor, _HorizonColor, _BottomColor, _SunColor;
                half _SunSize, _Stars;
            CBUFFER_END
            float3 _LS_SunDir;      // towards the sun
            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(i.positionOS.xyz);
                o.dir = i.positionOS.xyz;
                return o;
            }
            float Hash(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
            half4 Frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                half up = saturate(d.y);
                half3 c = lerp(_HorizonColor.rgb, _TopColor.rgb, pow(up, 0.55));
                c = lerp(c, _BottomColor.rgb, saturate(-d.y * 3.0));
                float3 sunDir = normalize(_LS_SunDir + float3(0, 1e-4, 0));
                float sd = saturate(dot(d, sunDir));
                c += _SunColor.rgb * (pow(sd, 48.0) * 0.45 + pow(sd, 6.0) * 0.12 + smoothstep(1.0 - _SunSize, 1.0 - _SunSize * 0.5, sd) * 1.5);
                if (_Stars > 0)
                {
                    float3 cell = floor(d * 220.0);
                    half star = step(0.996, Hash(cell)) * up;
                    c += star * _Stars;
                }
                return half4(c, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

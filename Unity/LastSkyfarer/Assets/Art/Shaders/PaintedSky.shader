// The Last Skyfarer: painted sky (skybox). A three-colour gradient, a soft sun glow, two layers of drifting painted
// clouds lit from the sun's side and, at night, faint stars.
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
        _BrushNoise ("Brush noise", 2D) = "gray" {}
        _CloudLit ("Cloud, lit side", Color) = (1, 0.98, 0.95, 1)
        _CloudShade ("Cloud, shaded side", Color) = (0.72, 0.74, 0.86, 1)
        _CloudCover ("Cloud cover", Range(0, 1)) = 0.45
        _CloudSpeed ("Cloud drift", Float) = 0.004
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
                half _SunSize, _Stars, _CloudCover;
                half4 _CloudLit, _CloudShade;
                float _CloudSpeed;
                float4 _BrushNoise_ST;
            CBUFFER_END
            TEXTURE2D(_BrushNoise); SAMPLER(sampler_BrushNoise);
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
                // Painted clouds on a dome: two noise layers, thicker towards the horizon, brighter towards the sun.
                if (d.y > -0.02)
                {
                    float2 dome = d.xz / (d.y + 0.18);
                    float t = _Time.y * _CloudSpeed;
                    half a = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, dome * 0.22 + float2(t, t * 0.3)).r;
                    half b = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, dome * 0.61 - float2(t * 0.6, t * 1.4)).g;
                    half shape = a * 0.7 + b * 0.45;
                    half cover = smoothstep(1.1 - _CloudCover, 1.35 - _CloudCover * 0.7, shape) * saturate((d.y + 0.02) * 8.0);
                    half lit = saturate(0.45 + 0.55 * pow(sd, 3.0) + (b - 0.5) * 0.6);
                    half3 cloud = lerp(_CloudShade.rgb, _CloudLit.rgb, lit) + _SunColor.rgb * pow(sd, 12.0) * 0.4;
                    c = lerp(c, cloud, cover * 0.92);
                }
                if (_Stars > 0)
                {
                    float3 cell = floor(d * 220.0);
                    half star = step(0.996, Hash(cell)) * up * (1.0 - _CloudCover * 0.5);
                    c += star * _Stars;
                }
                return half4(c, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

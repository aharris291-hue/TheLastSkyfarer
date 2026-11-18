// The Last Skyfarer: Brindle Isle's painted ground (polish pass 1). Blends meadow grass (two greens with sun-bleached
// patches), worn dirt and cobbles by the terrain's vertex paint (R grass, G dirt, B cobbles, A wildflowers), with
// brush-stroke relief, soft light, screen-space ambient occlusion and fog. One texture, sampled twice.
Shader "LastSkyfarer/PainterlyGround"
{
    Properties
    {
        _BrushNoise ("Brush noise", 2D) = "gray" {}
        _GrassA ("Grass A", Color) = (0.5, 0.66, 0.29, 1)
        _GrassB ("Grass B", Color) = (0.3, 0.48, 0.21, 1)
        _GrassDry ("Sun-bleached grass", Color) = (0.74, 0.74, 0.38, 1)
        _DirtA ("Dirt A", Color) = (0.71, 0.58, 0.42, 1)
        _DirtB ("Dirt B", Color) = (0.6, 0.48, 0.33, 1)
        _CobbleA ("Cobbles A", Color) = (0.79, 0.71, 0.59, 1)
        _CobbleB ("Cobbles mortar", Color) = (0.55, 0.49, 0.41, 1)
        _FlowerA ("Wildflowers A", Color) = (0.95, 0.85, 0.35, 1)
        _FlowerB ("Wildflowers B", Color) = (0.93, 0.55, 0.68, 1)
        _Bump ("Brush relief", Range(0, 2)) = 0.8
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _BrushNoise_ST;
            half4 _GrassA, _GrassB, _GrassDry, _DirtA, _DirtB, _CobbleA, _CobbleB, _FlowerA, _FlowerB;
            half _Bump;
        CBUFFER_END
        TEXTURE2D(_BrushNoise); SAMPLER(sampler_BrushNoise);
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
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; half4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; half3 normalWS : TEXCOORD1; half4 paint : COLOR; half fog : TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(i.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.paint = i.color;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half3 BrushBump(half3 n, float3 positionWS, half height)
            {
                float3 dpdx = ddx(positionWS), dpdy = ddy(positionWS);
                float dhdx = ddx(height), dhdy = ddy(height);
                float3 r1 = cross(dpdy, n), r2 = cross(n, dpdx);
                float det = dot(dpdx, r1);
                return normalize(abs(det) * n - sign(det) * (dhdx * r1 + dhdy * r2));
            }
            float2 Hash2(float2 p)
            {
                p = float2(dot(p, float2(127.1, 311.7)), dot(p, float2(269.5, 183.3)));
                return frac(sin(p) * 43758.5453);
            }
            // Cobblestones: a Voronoi pattern (nearest and second-nearest cell) gives rounded stones and mortar lines;
            // each stone gets its own shade.
            void Cobbles(float2 w, out half stone, out half shade)
            {
                float2 g = floor(w), f = frac(w);
                float d1 = 8.0, d2 = 8.0; float2 id = 0;
                [unroll] for (int y = -1; y <= 1; y++)
                [unroll] for (int x = -1; x <= 1; x++)
                {
                    float2 o = float2(x, y);
                    float2 r = o + 0.15 + 0.7 * Hash2(g + o) - f;
                    float d = dot(r, r);
                    if (d < d1) { d2 = d1; d1 = d; id = g + o; } else if (d < d2) d2 = d;
                }
                float edge = sqrt(d2) - sqrt(d1);
                stone = smoothstep(0.04, 0.2, edge);
                shade = Hash2(id).x;
            }
            half4 Frag(Varyings i) : SV_Target
            {
                float2 w = i.positionWS.xz;
                half4 big = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, w / 38.0);   // meadow-scale variation
                half4 fine = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, w / 2.3);   // brush strokes
                half4 macro = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, w / 160.0);  // field-scale light and dark
                half4 p = i.paint;
                half3 grass = lerp(_GrassA.rgb, _GrassB.rgb, saturate(big.r * 1.3 - 0.15 + (fine.g - 0.5) * 0.5));
                grass = lerp(grass, _GrassDry.rgb, smoothstep(0.62, 0.85, big.g) * 0.55);
                grass *= 0.78 + macro.r * 0.38;                                              // cloud-shadow-like patches
                grass = lerp(grass, grass * half3(0.82, 0.95, 1.05), smoothstep(0.55, 0.8, macro.g) * 0.6);   // cooler hollows
                half strokes = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, float2(w.x * 0.9 + w.y * 0.35, w.y * 0.9 - w.x * 0.35) / 1.1).r;
                grass *= 0.9 + strokes * 0.2;                                                // painted grass strokes
                half3 flowers = lerp(_FlowerA.rgb, _FlowerB.rgb, step(0.5, fine.b));
                grass = lerp(grass, flowers, p.a * smoothstep(0.72, 0.8, fine.r) * 0.8);
                half3 dirt = lerp(_DirtA.rgb, _DirtB.rgb, fine.r);
                // Cobbles: rounded stones from the fine strokes, darker mortar between them.
                half stone, shade;
                Cobbles(w / 0.55, stone, shade);
                half3 cobble = lerp(_CobbleB.rgb, _CobbleA.rgb * (0.82 + shade * 0.3) * (0.92 + fine.g * 0.16), stone);
                // Paint blending with a ragged, brushed edge.
                half g = saturate(p.g * 1.7 - 0.25 + (fine.r - 0.5) * 0.7);
                half b = saturate(p.b * 1.7 - 0.25 + (fine.g - 0.5) * 0.7);
                half3 col = lerp(lerp(grass, dirt, g), cobble, b);
                col *= 0.93 + fine.b * 0.14;
                half height = lerp(fine.r * 0.4, stone, b) + g * fine.g * 0.3;

                half3 n = BrushBump(normalize(i.normalWS), i.positionWS, height * _Bump * 0.05);
                Light sun = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                #if defined(_SCREEN_SPACE_OCCLUSION)
                    AmbientOcclusionFactor ssao = GetScreenSpaceAmbientOcclusion(GetNormalizedScreenSpaceUV(i.positionCS));
                    half aoI = ssao.indirectAmbientOcclusion, aoD = ssao.directAmbientOcclusion;
                #else
                    half aoI = 1.0, aoD = 1.0;
                #endif
                half wrap = saturate(dot(n, sun.direction) * 0.8 + 0.2);
                half3 light = sun.color * (wrap * sun.shadowAttenuation * sun.distanceAttenuation * aoD) + SampleSH(n) * aoI;
                #if defined(_ADDITIONAL_LIGHTS)
                    uint count = GetAdditionalLightsCount();
                    LIGHT_LOOP_BEGIN(count)
                        Light l = GetAdditionalLight(lightIndex, i.positionWS);
                        light += l.color * (saturate(dot(n, l.direction) * 0.8 + 0.2) * l.distanceAttenuation * l.shadowAttenuation);
                    LIGHT_LOOP_END
                #endif
                return half4(MixFog(col * light, i.fog), 1);
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
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            float4 Vert(Attributes i) : SV_POSITION
            {
                float3 ws = TransformObjectToWorld(i.positionOS.xyz);
                float4 cs = TransformWorldToHClip(ApplyShadowBias(ws, TransformObjectToWorldNormal(i.normalOS), _LightDirection));
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

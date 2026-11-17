// The Last Skyfarer: painterly surface for URP (port of M_Painterly_Surface / M_Painterly_Foliage, STYLE_GUIDE 5, D-27).
// Two paint colours mixed by a world-aligned brush-noise texture, a separate colour on upward faces (grass on rock),
// darker low down, a little paint grain, and an optional gentle wind sway for foliage. Opaque, one texture sample,
// simple diffuse light: cheap enough for Low on integrated graphics.
Shader "LastSkyfarer/Painterly"
{
    Properties
    {
        _BrushNoise ("Brush noise", 2D) = "gray" {}
        _ColorA ("Colour A", Color) = (0.73, 0.65, 0.54, 1)
        _ColorB ("Colour B", Color) = (0.61, 0.52, 0.41, 1)
        _TopColorA ("Top colour A", Color) = (0.5, 0.65, 0.28, 1)
        _TopColorB ("Top colour B", Color) = (0.37, 0.54, 0.23, 1)
        _TopAmount ("Top amount", Range(0, 1)) = 0
        _TopStart ("Top start", Range(0, 1)) = 0.6
        _BrushScale ("Brush scale (m)", Float) = 4
        _StrokeMix ("Stroke mix", Range(0, 1)) = 0.4
        _ShadeBottom ("Shade bottom (m)", Float) = -120
        _ShadeRange ("Shade range (m)", Float) = 120
        _ShadeAmount ("Shade amount", Range(0, 1)) = 0.65
        _WindAmount ("Wind amount (m)", Float) = 0
        _WindSpeed ("Wind speed", Float) = 1.3
        _SwayHeight ("Sway height (m)", Float) = 4
        _Emission ("Emission", Color) = (0, 0, 0, 0)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        CBUFFER_START(UnityPerMaterial)
            float4 _BrushNoise_ST;
            half4 _ColorA, _ColorB, _TopColorA, _TopColorB, _Emission;
            half _TopAmount, _TopStart, _StrokeMix, _ShadeAmount;
            float _BrushScale, _ShadeBottom, _ShadeRange, _WindAmount, _WindSpeed, _SwayHeight;
        CBUFFER_END
        TEXTURE2D(_BrushNoise); SAMPLER(sampler_BrushNoise);

        // Gentle sway, phase-shifted across the island, none at the plant's base.
        float3 Sway(float3 positionWS)
        {
            if (_WindAmount <= 0) return positionWS;
            float3 origin = TransformObjectToWorld(float3(0, 0, 0));
            float s = sin(_Time.y * _WindSpeed + (positionWS.x + positionWS.z) * 0.3);
            float height = saturate((positionWS.y - origin.y) / max(_SwayHeight, 0.01));
            return positionWS + float3(0.6, 0, 1.0) * (s * _WindAmount * height);
        }
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
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                half3 normalWS : TEXCOORD1;
                half4 fogAndVertexLight : TEXCOORD2;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings Vert(Attributes i)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(i);
                UNITY_TRANSFER_INSTANCE_ID(i, o);
                float3 ws = Sway(TransformObjectToWorld(i.positionOS.xyz));
                o.positionWS = ws;
                o.positionCS = TransformWorldToHClip(ws);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.fogAndVertexLight.x = ComputeFogFactor(o.positionCS.z);
                #ifdef _ADDITIONAL_LIGHTS_VERTEX
                    o.fogAndVertexLight.yzw = VertexLighting(ws, o.normalWS);
                #endif
                return o;
            }

            half4 Frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                half3 n = normalize(i.normalWS);
                float3 p = i.positionWS / max(_BrushScale, 0.01);
                float2 uv = p.xz + p.y * 0.7;             // planar from the top, nudged by height so walls do not smear
                half4 tex = SAMPLE_TEXTURE2D(_BrushNoise, sampler_BrushNoise, uv);
                half paint = lerp(tex.r, tex.g, _StrokeMix);
                half3 col = lerp(_ColorA.rgb, _ColorB.rgb, paint);
                half topMask = saturate((n.y - _TopStart) * 5.0) * _TopAmount;
                col = lerp(col, lerp(_TopColorA.rgb, _TopColorB.rgb, paint), topMask);
                half low = saturate((i.positionWS.y - _ShadeBottom) / max(_ShadeRange, 0.01));
                col = lerp(col * _ShadeAmount, col, low);
                col *= 0.92 + tex.b * 0.16;               // paint grain

                float4 shadowCoord = TransformWorldToShadowCoord(i.positionWS);
                Light sun = GetMainLight(shadowCoord);
                half ndl = dot(n, sun.direction);
                half wrap = saturate(ndl * 0.8 + 0.2);    // soft, painted terminator
                half3 light = sun.color * (wrap * sun.shadowAttenuation * sun.distanceAttenuation);
                light += SampleSH(n);
                #ifdef _ADDITIONAL_LIGHTS_VERTEX
                    light += i.fogAndVertexLight.yzw;
                #elif defined(_ADDITIONAL_LIGHTS)
                    uint count = GetAdditionalLightsCount();
                    LIGHT_LOOP_BEGIN(count)
                        Light l = GetAdditionalLight(lightIndex, i.positionWS);
                        light += l.color * (saturate(dot(n, l.direction) * 0.8 + 0.2) * l.distanceAttenuation * l.shadowAttenuation);
                    LIGHT_LOOP_END
                #endif
                half3 c = col * light + _Emission.rgb;
                c = MixFog(c, i.fogAndVertexLight.x);
                return half4(c, 1);
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
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            float3 _LightDirection;
            float3 _LightPosition;
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            float4 Vert(Attributes i) : SV_POSITION
            {
                UNITY_SETUP_INSTANCE_ID(i);
                float3 ws = Sway(TransformObjectToWorld(i.positionOS.xyz));
                float3 nws = TransformObjectToWorldNormal(i.normalOS);
                #if _CASTING_PUNCTUAL_LIGHT_SHADOW
                    float3 dir = normalize(_LightPosition - ws);
                #else
                    float3 dir = _LightDirection;
                #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(ws, nws, dir));
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
            #pragma multi_compile_instancing
            struct Attributes { float4 positionOS : POSITION; UNITY_VERTEX_INPUT_INSTANCE_ID };
            float4 Vert(Attributes i) : SV_POSITION
            {
                UNITY_SETUP_INSTANCE_ID(i);
                return TransformWorldToHClip(Sway(TransformObjectToWorld(i.positionOS.xyz)));
            }
            half4 Frag() : SV_Target { return 0; }
            ENDHLSL
        }
    }
    FallBack Off
}

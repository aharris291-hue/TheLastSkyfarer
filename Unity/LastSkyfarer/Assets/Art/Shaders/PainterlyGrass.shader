// The Last Skyfarer: instanced meadow grass and wildflowers (polish pass 1). Blades darker at the root and sunlit at
// the tip, coloured to match the ground beneath, swaying in gusts, shrinking away towards the edge of the grass radius
// (_LS_GrassFade, set by IslandGround) so nothing pops. Lit softly from both sides like thin leaves.
Shader "LastSkyfarer/PainterlyGrass"
{
    Properties
    {
        _BrushNoise ("Brush noise", 2D) = "gray" {}
        _Root ("Root", Color) = (0.24, 0.4, 0.17, 1)
        _TipA ("Tip A", Color) = (0.62, 0.79, 0.34, 1)
        _TipB ("Tip B", Color) = (0.78, 0.78, 0.4, 1)
        _Wind ("Wind (m)", Float) = 0.12
        _WindSpeed ("Wind speed", Float) = 1.7
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        Cull Off
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            CBUFFER_START(UnityPerMaterial)
                float4 _BrushNoise_ST;
                half4 _Root, _TipA, _TipB;
                float _Wind, _WindSpeed;
            CBUFFER_END
            TEXTURE2D(_BrushNoise); SAMPLER(sampler_BrushNoise);
            float4 _LS_GrassFade;     // camera position, radius
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; half4 color : COLOR; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float3 positionWS : TEXCOORD0; half3 normalWS : TEXCOORD1; half4 color : COLOR; half3 tint : TEXCOORD2; half fog : TEXCOORD3; };
            Varyings Vert(Attributes i)
            {
                UNITY_SETUP_INSTANCE_ID(i);
                Varyings o;
                float3 root = TransformObjectToWorld(float3(0, 0, 0));
                float d = distance(root.xz, _LS_GrassFade.xz);
                float fade = saturate((_LS_GrassFade.w - d) / (_LS_GrassFade.w * 0.25));     // shrink near the edge
                float3 pos = i.positionOS.xyz * fade;
                float3 ws = TransformObjectToWorld(pos);
                float h = i.color.a;                                                             // 0 root .. 1 tip
                float gust = 0.55 + 0.45 * sin(_Time.y * 0.45 + root.x * 0.05 + root.z * 0.03);
                float s = sin(_Time.y * _WindSpeed + root.x * 0.35 + root.z * 0.25);
                ws += float3(0.6, 0, 1.0) * (s * gust * _Wind * h * h);
                o.positionWS = ws;
                o.positionCS = TransformWorldToHClip(ws);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.color = i.color;
                half var = SAMPLE_TEXTURE2D_LOD(_BrushNoise, sampler_BrushNoise, root.xz / 38.0, 0).g;
                o.tint = lerp(_TipA.rgb, _TipB.rgb, smoothstep(0.55, 0.85, var) * 0.6) * (0.85 + i.color.r * 0.3);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }
            half4 Frag(Varyings i, bool front : SV_IsFrontFace) : SV_Target
            {
                half3 n = normalize(i.normalWS) * (front ? 1 : -1);
                half h = i.color.a;
                half3 col = lerp(_Root.rgb, i.tint, saturate(h * 1.2));
                col = lerp(col, i.color.rgb, i.color.b > 0.5 ? 1 : 0);                           // flower heads keep their own colour
                Light sun = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                half diffuse = saturate(dot(n, sun.direction)) * 0.6 + 0.4;                      // thin leaves: lit from both sides
                half3 light = sun.color * (diffuse * sun.shadowAttenuation) + SampleSH(half3(0, 1, 0));
                half3 c = col * light * (0.55 + 0.45 * h);
                return half4(MixFog(c, i.fog), 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}

// The Last Skyfarer: draws a wind volume as a few flowing ribbons along its line (hidden wind stays invisible until
// it is revealed). Cheap: three LineRenderers per volume, one additive material.
using UnityEngine;

namespace LastSkyfarer.World
{
    [RequireComponent(typeof(WindVolume))]
    public class WindRibbons : MonoBehaviour
    {
        public Material Material;
        public int Strands = 3;
        public float Width = 0.7f;
        WindVolume wind;
        LineRenderer[] lines;

        void Start()
        {
            wind = GetComponent<WindVolume>();
            var pts = wind.WorldPoints();
            Vector3 along = (pts[pts.Count - 1] - pts[0]).normalized;
            Vector3 side = Vector3.Cross(along, Mathf.Abs(along.y) > 0.9f ? Vector3.forward : Vector3.up).normalized;
            Vector3 up = Vector3.Cross(side, along).normalized;
            lines = new LineRenderer[Strands];
            for (int s = 0; s < Strands; s++)
            {
                var go = new GameObject("Ribbon_" + s);
                go.transform.SetParent(transform, false);
                var lr = go.AddComponent<LineRenderer>();
                lr.sharedMaterial = Material;
                lr.textureMode = LineTextureMode.Tile;
                lr.textureScale = new Vector2(1f, 1f);
                lr.widthMultiplier = Width;
                lr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                lr.receiveShadows = false;
                float a = s * Mathf.PI * 2f / Strands;
                Vector3 offset = (side * Mathf.Cos(a) + up * Mathf.Sin(a)) * wind.Radius * 0.45f;
                // Resample each segment so long lines get a gentle wave.
                var list = new System.Collections.Generic.List<Vector3>();
                for (int i = 0; i < pts.Count - 1; i++)
                {
                    int steps = Mathf.Max(1, Mathf.CeilToInt(Vector3.Distance(pts[i], pts[i + 1]) / 8f));
                    for (int k = 0; k < steps; k++)
                    {
                        float t = (float)k / steps;
                        Vector3 p = Vector3.Lerp(pts[i], pts[i + 1], t);
                        float wave = Mathf.Sin((list.Count * 0.7f) + s * 2f) * wind.Radius * 0.12f;
                        list.Add(p + offset + up * wave);
                    }
                }
                list.Add(pts[pts.Count - 1] + offset);
                lr.positionCount = list.Count;
                lr.SetPositions(list.ToArray());
                var c = new Color(1f, 1f, 1f, 0.55f + 0.15f * s);
                lr.startColor = lr.endColor = c;
                lines[s] = lr;
            }
            wind.OnVisibilityChanged += Refresh;
            Refresh();
        }

        void Refresh()
        {
            foreach (var l in lines) l.enabled = wind.IsActive;
        }
    }
}

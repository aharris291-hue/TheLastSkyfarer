// The Last Skyfarer: wind currents, updrafts and crosswinds (GDD 2.2), ported from the Unreal version.
// A volume is a polyline (its child points, or the Points list) plus a radius.
using System.Collections.Generic;
using UnityEngine;

namespace LastSkyfarer.World
{
    public enum WindType { Current, Updraft, Crosswind }

    public struct WindSample
    {
        public Vector3 Velocity;     // m/s
        public bool HoldAltitude;    // a current is cancelling the glider's sink
        public bool Inside;
    }

    public class WindVolume : MonoBehaviour
    {
        public static readonly List<WindVolume> All = new List<WindVolume>();

        public WindType Type = WindType.Current;
        [Tooltip("World-space points along the current or column. Empty = use child transforms.")]
        public List<Vector3> Points = new List<Vector3>();
        [Min(0.5f)] public float Radius = 6f;
        [Tooltip("Push speed for currents (8-20) and crosswinds, lift for updrafts (4-9), m/s.")] [Min(0f)] public float Strength = 14f;
        [Range(0f, 1f)] public float EdgeFalloff = 0.4f;
        [Tooltip("Invisible and inactive until revealed (by Piko or the Wind Resonator).")] public bool StartsHidden;
        [Tooltip("The impossible current glows Aerian blue.")] public bool ImpossibleRoute;

        public bool Revealed { get; private set; }
        public bool IsActive => !StartsHidden || Revealed;
        public event System.Action OnVisibilityChanged;

        void OnEnable() { if (!All.Contains(this)) All.Add(this); }
        void OnDisable() { All.Remove(this); }

        public IList<Vector3> WorldPoints()
        {
            if (Points.Count >= 2) return Points;
            var list = new List<Vector3>();
            foreach (Transform t in transform) list.Add(t.position);
            if (list.Count < 2) { list.Clear(); list.Add(transform.position); list.Add(transform.position + transform.forward * 10f); }
            return list;
        }

        public void Reveal()
        {
            if (Revealed) return;
            Revealed = true;
            OnVisibilityChanged?.Invoke();
        }

        /// <summary>Closest point on the polyline; t is the segment parameter, seg the segment index.</summary>
        public Vector3 Closest(Vector3 p, out int seg, out float t)
        {
            var pts = WorldPoints();
            float best = float.MaxValue;
            Vector3 bestPoint = pts[0];
            seg = 0; t = 0f;
            for (int i = 0; i < pts.Count - 1; i++)
            {
                Vector3 a = pts[i], b = pts[i + 1], ab = b - a;
                float u = Mathf.Clamp01(Vector3.Dot(p - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-6f));
                Vector3 c = a + ab * u;
                float d = (p - c).sqrMagnitude;
                if (d < best) { best = d; bestPoint = c; seg = i; t = u; }
            }
            return bestPoint;
        }

        public float DistanceTo(Vector3 p) => Vector3.Distance(Closest(p, out _, out _), p);

        public WindSample Sample(Vector3 p)
        {
            var o = new WindSample();
            if (!IsActive) return o;
            var pts = WorldPoints();
            Vector3 c = Closest(p, out int seg, out float t);
            float dist = Vector3.Distance(c, p);
            if (dist > Radius) return o;
            Vector3 dir = (pts[seg + 1] - pts[seg]).normalized;
            // Past the ends of the line the wind stops.
            if (Type == WindType.Current && ((seg == 0 && t <= 0f && Vector3.Dot(p - pts[0], dir) < -0.01f) ||
                (seg == pts.Count - 2 && t >= 1f && Vector3.Dot(p - pts[pts.Count - 1], dir) > 0.01f)))
                return o;
            float speed = Strength * Mathf.Lerp(1f, EdgeFalloff, dist / Mathf.Max(Radius, 0.01f));
            o.Inside = true;
            switch (Type)
            {
                case WindType.Current: o.Velocity = dir * speed; o.HoldAltitude = true; break;
                case WindType.Updraft: o.Velocity = Vector3.up * speed; break;
                case WindType.Crosswind: o.Velocity = transform.right * speed; break;
            }
            return o;
        }

        /// <summary>Sum of all active volumes at a point.</summary>
        public static WindSample SampleAll(Vector3 p)
        {
            var sum = new WindSample();
            foreach (var v in All)
            {
                var s = v.Sample(p);
                if (!s.Inside) continue;
                sum.Velocity += s.Velocity;
                sum.HoldAltitude |= s.HoldAltitude;
                sum.Inside = true;
            }
            return sum;
        }

        public static int RevealHiddenNear(Vector3 p, float range)
        {
            int n = 0;
            foreach (var v in All)
                if (v.StartsHidden && !v.Revealed && v.DistanceTo(p) <= range) { v.Reveal(); n++; }
            return n;
        }

        public static float DistanceToNearestHidden(Vector3 p)
        {
            float best = float.MaxValue;
            foreach (var v in All)
                if (v.StartsHidden && !v.Revealed) best = Mathf.Min(best, v.DistanceTo(p));
            return best;
        }

        void OnDrawGizmos()
        {
            var pts = WorldPoints();
            Gizmos.color = ImpossibleRoute ? new Color(0.3f, 0.7f, 1f) : new Color(0.8f, 0.95f, 1f);
            for (int i = 0; i < pts.Count - 1; i++) Gizmos.DrawLine(pts[i], pts[i + 1]);
        }
    }
}

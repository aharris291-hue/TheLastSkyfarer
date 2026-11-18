// The Last Skyfarer: third-person camera (GDD 1). Orbits Kieran with mouse/right stick, sits over his shoulder,
// pulls back and widens while gliding fast, and pushes in when a wall is behind it.
using UnityEngine;

namespace LastSkyfarer.Player
{
    public class ThirdPersonCamera : MonoBehaviour
    {
        public KieranController Target;
        public Camera Cam;
        public float Distance = 3.2f;
        public float GlideDistance = 6f;
        public float ShoulderOffset = 0.45f;
        public float PivotHeight = 1.55f;
        public float BaseFOV = 80f;
        public float MaxGlideFOV = 95f;
        public float MinPitch = -60f, MaxPitch = 70f;
        public float LookSensitivity = 1f;
        public bool InvertY;
        public LayerMask CollisionMask = ~0;

        public float Yaw { get; set; }
        public float Pitch { get; set; } = 12f;
        float currentDistance;

        void Start()
        {
            if (!Cam) Cam = GetComponentInChildren<Camera>();
            if (Target)
            {
                Yaw = Target.transform.eulerAngles.y;
                Target.CameraYawSource = transform;
            }
            currentDistance = Distance;
        }

        void LateUpdate()
        {
            if (!Target) return;
            float dt = Time.deltaTime;
            var settings = LastSkyfarer.Core.GameSettings.Current;
            Vector2 look = Target.Input.LookValue * LookSensitivity * settings.LookSensitivity;
            bool invert = InvertY ^ settings.InvertY;
            Yaw += look.x;
            Pitch = Mathf.Clamp(Pitch - look.y * (invert ? -1f : 1f), MinPitch, MaxPitch);

            bool gliding = Target.Mode == MoveMode.Gliding;
            float alpha = gliding ? Mathf.Lerp(0.4f, 1f, Mathf.InverseLerp(Target.Glider.TrimSpeed * 0.5f, Target.Glider.MaxDiveSpeed, Target.GlideState.Speed)) : 0f;
            float wantDistance = Mathf.Lerp(Distance, GlideDistance, alpha);
            float wantFov = Mathf.Lerp(BaseFOV, MaxGlideFOV, alpha);

            Quaternion rot = Quaternion.Euler(Pitch, Yaw, 0f);
            transform.SetPositionAndRotation(Target.transform.position + Vector3.up * PivotHeight, Quaternion.Euler(0f, Yaw, 0f));
            Vector3 pivot = transform.position + rot * new Vector3(ShoulderOffset, 0f, 0f);
            Vector3 back = rot * Vector3.back;
            float free = wantDistance;
            if (Physics.SphereCast(pivot, 0.2f, back, out RaycastHit hit, wantDistance, CollisionMask, QueryTriggerInteraction.Ignore)
                && !hit.collider.transform.IsChildOf(Target.transform))
                free = Mathf.Max(0.4f, hit.distance - 0.1f);
            currentDistance = free < currentDistance ? free : Mathf.Lerp(currentDistance, free, 1f - Mathf.Exp(-3f * dt));
            if (Cam)
            {
                Cam.transform.SetPositionAndRotation(pivot + back * currentDistance, rot);
                Cam.fieldOfView = Mathf.Lerp(Cam.fieldOfView, wantFov, 1f - Mathf.Exp(-3f * dt));
            }
        }
    }
}

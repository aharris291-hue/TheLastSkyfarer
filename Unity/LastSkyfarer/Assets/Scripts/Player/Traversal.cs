// The Last Skyfarer: mantle, ledge hang and shimmy, and climbing (GDD 1), ported from the Unreal version.
// Climbable surfaces carry a Climbable component. Metres and seconds.
using UnityEngine;

namespace LastSkyfarer.Player
{
    public enum TraversalState { None, Mantling, Hanging, Climbing }

    public struct Ledge
    {
        public Vector3 Top, WallPoint, WallNormal;
        public float Height;        // ledge top above the feet
        public bool Climbable, HasTop;
    }

    /// <summary>Marks a wall Kieran can climb.</summary>
    public class Climbable : MonoBehaviour { }

    [RequireComponent(typeof(KieranController))]
    public class Traversal : MonoBehaviour
    {
        [Header("Mantle")] public float MinMantleHeight = 0.5f, MaxMantleHeight = 1.8f, MantleDuration = 0.45f;
        [Header("Hang")] public float MaxHangReach = 2.3f, HangHeight = 2.0f, ShimmySpeed = 1.0f;
        [Header("Climb (GDD: 1.2 m/s, hop 1.5 m)")] public float ClimbSpeed = 1.2f, ClimbHopDistance = 1.5f;
        public float WallReach = 0.45f, RegrabCooldown = 0.4f;

        public TraversalState State { get; private set; }
        public bool IsBusy => State != TraversalState.None;

        KieranController k;
        CharacterController body;
        float cooldownUntil = -1f, mantleTime, mantleLength;
        bool autoRegrab;
        Vector3 mantleStart, mantleMid, mantleEnd, wallNormal;
        Vector2 stick;

        void Awake()
        {
            k = GetComponent<KieranController>();
            body = GetComponent<CharacterController>();
            k.TraversalJump = Jump;
        }

        static Vector3 Flat(Vector3 v) { v.y = 0f; return v.normalized; }
        float Feet => transform.position.y;          // the controller's pivot is at the feet
        float Radius => body.radius;
        float Height => body.height;

        bool TraceWall(Vector3 from, Vector3 dir, out RaycastHit hit)
        {
            return Physics.Raycast(from, dir, out hit, Radius + WallReach, ~0, QueryTriggerInteraction.Ignore)
                   && Mathf.Abs(hit.normal.y) < 0.3f && !hit.collider.transform.IsChildOf(transform);
        }

        bool CapsuleFits(Vector3 feet)
        {
            float r = Radius * 0.95f;
            Vector3 a = feet + Vector3.up * (r + 0.05f), b = feet + Vector3.up * (Height - r);
            foreach (var c in Physics.OverlapCapsule(a, b, r, ~0, QueryTriggerInteraction.Ignore))
                if (!c.transform.IsChildOf(transform)) return false;
            return true;
        }

        public bool FindLedge(Vector3 direction, out Ledge o)
        {
            o = new Ledge();
            Vector3 dir = Flat(direction);
            if (dir.sqrMagnitude < 0.5f) return false;
            Vector3 p = transform.position;
            RaycastHit wall = default;
            bool found = false;
            foreach (float z in new[] { 0.4f, 1.0f, 1.6f })   // knee, chest, head
                if (TraceWall(new Vector3(p.x, Feet + z, p.z), dir, out wall)) { found = true; break; }
            if (!found) return false;
            o.WallPoint = wall.point;
            o.WallNormal = Flat(wall.normal);
            o.Climbable = wall.collider.GetComponentInParent<Climbable>() != null;
            Vector3 probe = wall.point - o.WallNormal * 0.25f;
            Vector3 start = new Vector3(probe.x, Feet + MaxHangReach + 0.3f, probe.z);
            float down = MaxHangReach + 0.3f - (MinMantleHeight - 0.1f);
            if (Physics.SphereCast(start, 0.1f, Vector3.down, out RaycastHit top, down, ~0, QueryTriggerInteraction.Ignore)
                && top.normal.y > 0.7f && !top.collider.transform.IsChildOf(transform))
            {
                o.Top = top.point;
                o.Height = top.point.y - Feet;
                o.HasTop = CapsuleFits(o.Top - o.WallNormal * (Radius + 0.05f) + Vector3.up * 0.02f);
            }
            return true;
        }

        public TraversalState Classify(Ledge l, bool falling, bool pushing, float verticalSpeed)
        {
            if (l.HasTop && l.Height >= MinMantleHeight && l.Height <= MaxMantleHeight && (pushing || falling)) return TraversalState.Mantling;
            if (falling && l.HasTop && l.Height > MaxMantleHeight && l.Height <= MaxHangReach && verticalSpeed <= 0f) return TraversalState.Hanging;
            if (l.Climbable && pushing) return TraversalState.Climbing;
            return TraversalState.None;
        }

        void Update()
        {
            stick = k.Input.MoveValue;
            switch (State)
            {
                case TraversalState.None:
                    TryEnter();
                    if (autoRegrab && k.Mode == MoveMode.Grounded) autoRegrab = false;
                    break;
                case TraversalState.Mantling: TickMantle(Time.deltaTime); break;
                case TraversalState.Hanging: TickHang(Time.deltaTime); break;
                case TraversalState.Climbing: TickClimb(Time.deltaTime); break;
            }
            if (State != TraversalState.None && k.Input.AirBrake.WasPressedThisFrame()) Drop();
        }

        void TryEnter()
        {
            if (Time.time < cooldownUntil || (k.Mode != MoveMode.Grounded && k.Mode != MoveMode.Falling)) return;
            bool falling = k.Mode == MoveMode.Falling;
            Vector3 move = Flat(k.WorldMoveDirection);
            Vector3 dir = move;
            if (dir.sqrMagnitude < 0.5f && (falling || autoRegrab)) dir = transform.forward;
            if (dir.sqrMagnitude < 0.5f || !FindLedge(dir, out Ledge l)) return;
            bool pushing = Vector3.Dot(move, -l.WallNormal) > 0.5f;
            switch (Classify(l, falling, pushing || autoRegrab, k.Velocity.y))
            {
                case TraversalState.Mantling: StartMantle(l); break;
                case TraversalState.Hanging: StartHang(l); break;
                case TraversalState.Climbing:
                    if (TraceWall(transform.position + Vector3.up * (Height * 0.5f), -l.WallNormal, out RaycastHit w)) StartClimb(w);
                    break;
            }
        }

        void Place(Vector3 feet, Vector3 faceNormal)
        {
            body.enabled = false;
            transform.SetPositionAndRotation(feet, Quaternion.LookRotation(-faceNormal));
            body.enabled = true;
        }

        void StartMantle(Ledge l)
        {
            mantleStart = transform.position;
            mantleMid = new Vector3(mantleStart.x, l.Top.y + 0.05f, mantleStart.z);
            mantleEnd = l.Top - l.WallNormal * (Radius + 0.05f) + Vector3.up * 0.02f;
            mantleTime = 0f;
            mantleLength = MantleDuration * Mathf.Lerp(0.7f, 1.2f, Mathf.InverseLerp(MinMantleHeight, MaxHangReach, l.Height));
            wallNormal = l.WallNormal;
            State = TraversalState.Mantling;
            k.SetClimbing(true);
            transform.rotation = Quaternion.LookRotation(-wallNormal);
        }

        void StartHang(Ledge l)
        {
            wallNormal = l.WallNormal;
            Vector3 hang = l.WallPoint + wallNormal * (Radius + 0.02f);
            State = TraversalState.Hanging;
            k.SetClimbing(true);
            Place(new Vector3(hang.x, l.Top.y - HangHeight, hang.z), wallNormal);
        }

        void StartClimb(RaycastHit w)
        {
            wallNormal = Flat(w.normal);
            State = TraversalState.Climbing;
            autoRegrab = false;
            k.SetClimbing(true);
            Vector3 on = w.point + wallNormal * (Radius + 0.02f);
            Place(new Vector3(on.x, transform.position.y, on.z), wallNormal);
        }

        void End(bool grounded)
        {
            State = TraversalState.None;
            k.SetClimbing(false);
        }

        void TickMantle(float dt)
        {
            mantleTime += dt;
            float a = Mathf.Clamp01(mantleTime / Mathf.Max(mantleLength, 0.05f));
            Vector3 pos = a < 0.6f ? Vector3.Lerp(mantleStart, mantleMid, 1f - Mathf.Pow(1f - a / 0.6f, 2f))
                                   : Vector3.Lerp(mantleMid, mantleEnd, (a - 0.6f) / 0.4f);
            body.enabled = false;
            transform.position = pos;
            body.enabled = true;
            if (a >= 1f) End(true);
        }

        Vector3 Tangent => -Vector3.Cross(Vector3.up, wallNormal);

        void TickHang(float dt)
        {
            if (Mathf.Abs(stick.x) < 0.2f) return;
            Vector3 old = transform.position;
            body.Move(Tangent * Mathf.Sign(stick.x) * ShimmySpeed * dt);
            if (!FindLedge(-wallNormal, out Ledge l) || !l.HasTop || l.Height > MaxHangReach + 0.05f) Place(old, wallNormal);   // only while a ledge continues
        }

        void TickClimb(float dt)
        {
            Vector3 p = transform.position;
            if (!TraceWall(p + Vector3.up * (Height * 0.9f), -wallNormal, out _))
            {
                if (FindLedge(-wallNormal, out Ledge l) && l.HasTop) StartMantle(l); else Drop();   // reached the top
                return;
            }
            if (!TraceWall(p + Vector3.up * (Height * 0.5f), -wallNormal, out RaycastHit w)) { Drop(); return; }
            wallNormal = Flat(w.normal);
            Vector3 delta = Vector3.ClampMagnitude(Vector3.up * stick.y + Tangent * stick.x, 1f) * ClimbSpeed * dt;
            Vector3 on = w.point + wallNormal * (Radius + 0.02f);
            Vector3 target = new Vector3(on.x, p.y, on.z) + delta;
            transform.rotation = Quaternion.LookRotation(-wallNormal);
            CollisionFlags flags = body.Move(target - p);
            if (stick.y < -0.2f && (flags & CollisionFlags.Below) != 0) End(true);   // climbed down onto the ground
        }

        public bool Jump()
        {
            switch (State)
            {
                case TraversalState.Hanging:
                    if (FindLedge(-wallNormal, out Ledge l) && l.HasTop) StartMantle(l);
                    return true;
                case TraversalState.Climbing:
                {
                    Vector3 launch;
                    if (Mathf.Abs(stick.x) < 0.2f && stick.y < -0.2f)
                    {
                        launch = wallNormal * 4.5f + Vector3.up * 3f;   // back away from the wall
                        cooldownUntil = Time.time + RegrabCooldown;
                    }
                    else
                    {
                        float up = Mathf.Sqrt(2f * k.Gravity * ClimbHopDistance);   // hop up or sideways and re-grab
                        launch = Mathf.Abs(stick.x) >= 0.2f ? Tangent * Mathf.Sign(stick.x) * 3.5f + Vector3.up * up * 0.6f - wallNormal * 0.5f
                                                            : Vector3.up * up - wallNormal * 0.5f;
                        autoRegrab = true;
                        cooldownUntil = Time.time + 0.15f;
                    }
                    State = TraversalState.None;
                    k.Launch(launch);
                    return true;
                }
                case TraversalState.Mantling: return true;
                default: return false;
            }
        }

        public void Drop()
        {
            if (State != TraversalState.Hanging && State != TraversalState.Climbing) return;
            cooldownUntil = Time.time + RegrabCooldown;
            autoRegrab = false;
            End(false);
        }
    }
}

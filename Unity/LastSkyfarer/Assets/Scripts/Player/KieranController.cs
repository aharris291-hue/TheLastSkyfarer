// The Last Skyfarer: Kieran, the player character (GDD 1 and 2), ported from the Unreal version.
// Walk/run/sprint, coyote time and jump buffering, glider deploy and landing, recovery to the last safe ledge.
// Units are metres and seconds.
using LastSkyfarer.Glider;
using LastSkyfarer.World;
using UnityEngine;

namespace LastSkyfarer.Player
{
    public enum MoveMode { Grounded, Falling, Gliding, Climbing }

    [RequireComponent(typeof(CharacterController))]
    public class KieranController : MonoBehaviour
    {
        [Header("Movement (GDD 1)")]
        public float WalkSpeed = 1.8f;
        public float RunSpeed = 4.5f;
        public float SprintSpeed = 6.5f;
        [Tooltip("Sprint ends after this many seconds...")] public float SprintDuration = 4f;
        [Tooltip("...and cannot restart for this long.")] public float SprintCooldown = 2f;
        [Tooltip("Jump apex height, m.")] public float JumpHeight = 1.3f;
        public float Gravity = 9.8f;
        public float CoyoteTime = 0.12f;
        public float JumpBufferTime = 0.15f;
        [Range(0f, 1f)] public float AirControl = 0.4f;
        [Tooltip("Turn rate toward the move direction, deg/s.")] public float TurnRate = 720f;
        public float GroundAcceleration = 20f;

        [Header("Glider (GDD 2)")]
        public GliderParams Glider = new GliderParams();
        public bool HasGlider = true;
        public bool GlideAssist;
        [Tooltip("Can't deploy closer than this to the ground, m.")] public float MinDeployHeight = 1.5f;
        public float RollLandingStagger = 0.6f;

        [Header("Recovery (GDD 2.5)")]
        [Tooltip("Falling below this height returns Kieran to the last safe ledge, m.")] public float RecoveryY = -200f;
        public float SafePointInterval = 2f;

        public CharacterController Body { get; private set; }
        public PlayerInputs Input { get; private set; }
        public MoveMode Mode { get; private set; } = MoveMode.Falling;
        public GliderState GlideState => glide;
        public Vector3 Velocity => velocity;
        public bool Sprinting { get; private set; }
        public bool WalkMode { get; private set; }
        public Transform CameraYawSource;            // the camera rig; movement is relative to its yaw
        public System.Action OnGliderDeployed, OnGliderStowed, OnJumped;
        public System.Action<bool> OnGliderLanded;    // true = roll landing
        public System.Func<bool> TraversalJump;       // climbing hooks in here later

        readonly SafePointTracker safePoints = new SafePointTracker();
        GliderState glide;
        Vector3 velocity;
        float leftGroundTime = -100f, jumpPressedTime = -100f, sprintStart = -100f, sprintEnd = -100f, staggerUntil = -100f;
        bool jumpedSinceGrounded;

        void Awake()
        {
            Body = GetComponent<CharacterController>();
            Input = new PlayerInputs();
        }

        void OnEnable() => Input.Enable();
        void OnDisable() => Input.Disable();
        void OnDestroy() => Input.Dispose();

        void Start()
        {
            safePoints.SampleInterval = SafePointInterval;
            safePoints.Update(Time.timeAsDouble, transform.position, true);
        }

        float Now => Time.time;
        public Vector3 SafePoint => safePoints.SafePoint;

        void Update()
        {
            float dt = Time.deltaTime;
            if (dt <= 0f) return;

            if (Input.Jump.WasPressedThisFrame()) JumpPressed();
            if (Input.Sprint.WasPressedThisFrame()) StartSprint();
            if (Input.Sprint.WasReleasedThisFrame()) StopSprint();
            if (Input.WalkToggle.WasPressedThisFrame() && Mode != MoveMode.Gliding && Mode != MoveMode.Climbing) WalkMode = !WalkMode;
            if (Sprinting && Now - sprintStart >= SprintDuration) StopSprint();

            switch (Mode)
            {
                case MoveMode.Gliding: TickGlide(dt); break;
                case MoveMode.Climbing: break;   // the traversal component drives the body
                default: TickWalk(dt); break;
            }

            safePoints.SampleInterval = SafePointInterval;
            safePoints.Update(Time.timeAsDouble, transform.position, Mode == MoveMode.Grounded && Body.isGrounded);
            if (transform.position.y < RecoveryY) RecoverToSafePoint();
        }

        // ------------------------------------------------------------------ walking, running, jumping
        Vector3 MoveDirection()
        {
            Vector2 m = Input.MoveValue;
            float yaw = CameraYawSource ? CameraYawSource.eulerAngles.y : transform.eulerAngles.y;
            Quaternion q = Quaternion.Euler(0f, yaw, 0f);
            return q * new Vector3(m.x, 0f, m.y);
        }

        public Vector3 WorldMoveDirection => MoveDirection();

        /// <summary>Throws Kieran into the air with a velocity (climb hops, jump-offs).</summary>
        public void Launch(Vector3 v)
        {
            Mode = MoveMode.Falling;
            velocity = v;
            jumpedSinceGrounded = true;
        }

        public float TargetSpeed => Sprinting ? SprintSpeed : (WalkMode ? WalkSpeed : RunSpeed);

        void TickWalk(float dt)
        {
            bool grounded = Body.isGrounded;
            Vector3 wish = Now < staggerUntil ? Vector3.zero : MoveDirection();
            Vector3 horizontal = new Vector3(velocity.x, 0f, velocity.z);
            Vector3 target = wish * TargetSpeed;
            float accel = GroundAcceleration * (grounded ? 1f : AirControl);
            horizontal = Vector3.MoveTowards(horizontal, target, accel * dt);   // m/s² toward the wished speed

            if (grounded)
            {
                if (Mode != MoveMode.Grounded)
                {
                    Mode = MoveMode.Grounded;
                    jumpedSinceGrounded = false;
                    if (Now - jumpPressedTime <= JumpBufferTime) { jumpPressedTime = -100f; DoJump(); }
                }
                if (Mode == MoveMode.Grounded && velocity.y < 0f) velocity.y = -2f;   // keep the controller pressed to the floor
            }
            else if (Mode == MoveMode.Grounded)
            {
                Mode = MoveMode.Falling;
                leftGroundTime = Now;
            }
            if (!grounded || velocity.y > 0f) velocity.y -= Gravity * dt;

            velocity.x = horizontal.x;
            velocity.z = horizontal.z;
            if (wish.sqrMagnitude > 0.001f)
            {
                Quaternion face = Quaternion.LookRotation(new Vector3(wish.x, 0f, wish.z));
                transform.rotation = Quaternion.RotateTowards(transform.rotation, face, TurnRate * dt);
            }
            Body.Move(velocity * dt);
        }

        float JumpVelocity => Mathf.Sqrt(2f * Gravity * JumpHeight);

        void DoJump()
        {
            jumpedSinceGrounded = true;
            velocity.y = JumpVelocity;
            Mode = MoveMode.Falling;
            OnJumped?.Invoke();
        }

        public void JumpPressed()
        {
            if (TraversalJump != null && TraversalJump()) return;
            if (Mode == MoveMode.Gliding) { Stow(); return; }
            if (Mode == MoveMode.Falling)
            {
                if (!jumpedSinceGrounded && Now - leftGroundTime <= CoyoteTime) { DoJump(); return; }   // just walked off an edge
                if (TryDeploy()) return;
                jumpPressedTime = Now;   // buffered for the landing
                return;
            }
            if (Mode == MoveMode.Grounded) DoJump();
        }

        void StartSprint()
        {
            if (Now - sprintEnd < SprintCooldown) return;
            Sprinting = true;
            WalkMode = false;
            sprintStart = Now;
        }

        void StopSprint()
        {
            if (!Sprinting) return;
            Sprinting = false;
            sprintEnd = Now;
        }

        // ------------------------------------------------------------------ glider
        bool NearGround(float distance, out RaycastHit hit)
        {
            Vector3 start = transform.position + Vector3.up * (Body.radius + 0.05f);
            return Physics.SphereCast(start, Body.radius * 0.9f, Vector3.down, out hit, distance + 0.05f, ~0, QueryTriggerInteraction.Ignore);
        }

        public bool TryDeploy()
        {
            if (!HasGlider || Mode != MoveMode.Falling) return false;
            if (NearGround(MinDeployHeight, out _)) return false;
            glide = GliderModel.FromVelocity(velocity, Glider, transform.eulerAngles.y);
            Mode = MoveMode.Gliding;
            OnGliderDeployed?.Invoke();
            return true;
        }

        public void Stow()
        {
            if (Mode != MoveMode.Gliding) return;
            Mode = MoveMode.Falling;
            OnGliderStowed?.Invoke();
        }

        void TickGlide(float dt)
        {
            Vector2 m = Input.MoveValue;
            var input = new GliderInput { Pitch = m.y, Turn = m.x, AirBrake = Input.AirBrake.IsPressed(), Assist = GlideAssist };
            GliderStepResult step = GliderModel.Step(ref glide, input, Glider, dt);
            Vector3 v = step.AirDisplacement / dt;
            WindSample w = WindVolume.SampleAll(transform.position);
            if (w.Inside)
            {
                v += w.Velocity;
                if (w.HoldAltitude && v.y < 0f) v.y = 0f;
            }
            velocity = v;
            transform.rotation = Quaternion.Euler(0f, glide.Yaw, 0f);
            CollisionFlags flags = Body.Move(velocity * dt);
            if (velocity.y <= 0f && (Body.isGrounded || (flags & CollisionFlags.Below) != 0 || (NearGround(0.25f, out RaycastHit h) && h.normal.y >= 0.7f)))
                Land(glide.Speed);
        }

        void Land(float impactSpeed)
        {
            bool roll = GliderModel.IsRollLanding(impactSpeed, Glider);
            Mode = MoveMode.Grounded;
            velocity.y = -2f;
            if (roll)
            {
                velocity.x *= 0.3f;
                velocity.z *= 0.3f;
                staggerUntil = Now + RollLandingStagger;
            }
            jumpedSinceGrounded = false;
            OnGliderLanded?.Invoke(roll);
        }

        // ------------------------------------------------------------------ recovery and teleports
        public void RecoverToSafePoint()
        {
            Teleport(safePoints.HasSafePoint ? safePoints.SafePoint : transform.position, transform.eulerAngles.y);
            Mode = MoveMode.Falling;
        }

        public void Teleport(Vector3 position, float yaw)
        {
            if (Mode == MoveMode.Gliding) Stow();
            Body.enabled = false;
            transform.SetPositionAndRotation(position, Quaternion.Euler(0f, yaw, 0f));
            Body.enabled = true;
            Body.Move(Vector3.down * 0.001f);   // refresh isGrounded at the new spot (it is stale after a teleport)
            velocity = Vector3.zero;
            Mode = MoveMode.Falling;
        }

        public void SetClimbing(bool climbing)
        {
            Mode = climbing ? MoveMode.Climbing : MoveMode.Falling;
            velocity = Vector3.zero;
        }
    }
}

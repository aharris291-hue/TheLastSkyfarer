// The Last Skyfarer: drives Kieran's Animator from his movement (speed, grounded, jump, gliding, climbing).
using UnityEngine;

namespace LastSkyfarer.Player
{
    [RequireComponent(typeof(KieranController))]
    public class KieranAnimator : MonoBehaviour
    {
        public Animator Animator;
        static readonly int SpeedId = Animator.StringToHash("Speed"), GroundedId = Animator.StringToHash("Grounded"),
            GlidingId = Animator.StringToHash("Gliding"), ClimbingId = Animator.StringToHash("Climbing"),
            ClimbSpeedId = Animator.StringToHash("ClimbSpeed"), JumpId = Animator.StringToHash("Jump");

        KieranController k;
        Traversal traversal;
        float speed;

        void Awake()
        {
            k = GetComponent<KieranController>();
            traversal = GetComponent<Traversal>();
            if (!Animator) Animator = GetComponentInChildren<Animator>();
            k.OnJumped += () => { if (Animator) Animator.SetTrigger(JumpId); };
        }

        void LateUpdate()
        {
            if (!Animator) return;
            Vector3 v = k.Velocity;
            float horizontal = new Vector2(v.x, v.z).magnitude;
            speed = Mathf.Lerp(speed, horizontal, 1f - Mathf.Exp(-12f * Time.deltaTime));
            bool climbing = traversal && (traversal.State == TraversalState.Climbing || traversal.State == TraversalState.Hanging || traversal.State == TraversalState.Mantling);
            Animator.SetFloat(SpeedId, speed);
            Animator.SetBool(GroundedId, k.Mode == MoveMode.Grounded);
            Animator.SetBool(GlidingId, k.Mode == MoveMode.Gliding);
            Animator.SetBool(ClimbingId, climbing);
            float climbRate = traversal && traversal.State == TraversalState.Climbing ? Mathf.Abs(k.Input.MoveValue.y) + Mathf.Abs(k.Input.MoveValue.x) : 1f;
            Animator.SetFloat(ClimbSpeedId, traversal && traversal.State == TraversalState.Hanging ? 0f : Mathf.Clamp(climbRate, 0f, 1f));
        }
    }
}

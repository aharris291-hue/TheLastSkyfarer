// The Last Skyfarer: Elias's glider on Kieran's back. Shows the wing while he glides and closes both hands on the
// control bar with Humanoid hand IK, so the grip holds whatever the retargeted glide pose does with his arms.
// Lives on the model (the object with the Animator); the Animator layer needs its IK pass on (KieranSetup does that).
using UnityEngine;

namespace LastSkyfarer.Player
{
    [RequireComponent(typeof(Animator))]
    public class KieranGlideRig : MonoBehaviour
    {
        public KieranController Kieran;
        public GameObject Glider;               // wing, frame and bar; hidden unless gliding
        public Transform LeftGrip, RightGrip;   // where the palms close on the bar
        [Range(0f, 1f)] public float GripWeight = 1f;
        public float BlendTime = 0.2f;

        Animator anim;
        float weight;

        void Awake()
        {
            anim = GetComponent<Animator>();
            if (!Kieran) Kieran = GetComponentInParent<KieranController>();
            if (Glider) Glider.SetActive(false);
        }

        void Update()
        {
            bool gliding = Kieran && Kieran.Mode == MoveMode.Gliding;
            if (Glider && Glider.activeSelf != gliding) Glider.SetActive(gliding);
            weight = Mathf.MoveTowards(weight, gliding ? GripWeight : 0f, Time.deltaTime / Mathf.Max(0.01f, BlendTime));
        }

        public int IKCalls { get; private set; }

        void OnAnimatorIK(int layer)
        {
            IKCalls++;
            Grip(AvatarIKGoal.LeftHand, LeftGrip);
            Grip(AvatarIKGoal.RightHand, RightGrip);
        }

        void Grip(AvatarIKGoal goal, Transform target)
        {
            if (!target) return;
            anim.SetIKPositionWeight(goal, weight);
            anim.SetIKRotationWeight(goal, weight * 0.8f);
            if (weight <= 0f) return;
            anim.SetIKPosition(goal, target.position);
            anim.SetIKRotation(goal, target.rotation);
        }

        /// <summary>How far each hand is from its grip right now (for tests and the showcase), metres.</summary>
        public Vector2 GripError()
        {
            var l = anim.GetBoneTransform(HumanBodyBones.LeftHand);
            var r = anim.GetBoneTransform(HumanBodyBones.RightHand);
            return new Vector2(l && LeftGrip ? Vector3.Distance(l.position, LeftGrip.position) : -1f,
                               r && RightGrip ? Vector3.Distance(r.position, RightGrip.position) : -1f);
        }
    }
}

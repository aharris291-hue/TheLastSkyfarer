// The Last Skyfarer: the real Kieran prefab glides with the glider showing and both hands on the control bar.
#if UNITY_EDITOR
using System.Collections;
using LastSkyfarer.Player;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

namespace LastSkyfarer.Tests
{
    public class GlideGripTests
    {
        [UnityTest]
        public IEnumerator BothHandsReachTheBarWhileGliding()
        {
            var ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
            ground.transform.localScale = new Vector3(2000f, 1f, 2000f);
            ground.transform.position = new Vector3(0f, -0.5f, 0f);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/Kieran.prefab");
            var k = Object.Instantiate(prefab).GetComponent<KieranController>();
            var rig = k.GetComponentInChildren<KieranGlideRig>();
            Assert.IsNotNull(rig, "the prefab has its glider rig");
            Assert.IsFalse(rig.Glider.activeSelf, "glider hidden on the ground");
            // In the game the animator only poses Kieran while a camera sees him (CullUpdateTransforms); batchmode tests
            // never render, so animate regardless.
            rig.GetComponent<Animator>().cullingMode = AnimatorCullingMode.AlwaysAnimate;
            var cam = new GameObject("TestCamera").AddComponent<Camera>();
            k.HasGlider = true;
            k.Teleport(new Vector3(0f, 120f, 0f), 0f);
            yield return new WaitForSeconds(0.4f);
            Assert.IsTrue(k.TryDeploy());
            for (float t = 0f; t < 1.2f; t += Time.deltaTime)
            {
                cam.transform.position = k.transform.position + new Vector3(4f, 2f, -3f);
                cam.transform.LookAt(k.transform.position);
                yield return null;
            }
            Assert.AreEqual(MoveMode.Gliding, k.Mode);
            Assert.IsTrue(rig.Glider.activeSelf, "glider shows while gliding");
            Vector2 err = rig.GripError();
            var an = rig.GetComponent<Animator>();
            Vector3 Loc(Transform t) => t ? k.transform.InverseTransformPoint(t.position) : Vector3.positiveInfinity;
            Debug.Log($"LS_GRIP_DEBUG glide state {an.GetCurrentAnimatorStateInfo(0).IsName("Glide")}, IK calls {rig.IKCalls}, hands {Loc(an.GetBoneTransform(HumanBodyBones.LeftHand))} {Loc(an.GetBoneTransform(HumanBodyBones.RightHand))}, grips {Loc(rig.LeftGrip)} {Loc(rig.RightGrip)}, shoulders {Loc(an.GetBoneTransform(HumanBodyBones.LeftUpperArm))} {Loc(an.GetBoneTransform(HumanBodyBones.RightUpperArm))}, head {Loc(an.GetBoneTransform(HumanBodyBones.Head))}, hips {Loc(an.GetBoneTransform(HumanBodyBones.Hips))}");
            Debug.Log($"LS_GRIP left hand {err.x * 100f:F1} cm, right hand {err.y * 100f:F1} cm from the bar");
            Assert.Less(err.x, 0.06f, "left hand on the bar");
            Assert.Less(err.y, 0.06f, "right hand on the bar");
            k.Stow();
            yield return new WaitForSeconds(0.3f);
            Assert.IsFalse(rig.Glider.activeSelf, "glider folds away");
            Object.Destroy(k.gameObject); Object.Destroy(ground); Object.Destroy(cam.gameObject);
        }
    }
}
#endif

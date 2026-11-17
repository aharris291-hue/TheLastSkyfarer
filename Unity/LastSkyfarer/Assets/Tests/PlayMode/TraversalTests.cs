// The Last Skyfarer: mantle, hang and climb in play mode.
using System.Collections;
using LastSkyfarer.Player;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace LastSkyfarer.Tests
{
    public class TraversalTests
    {
        GameObject root, kieranGo;
        KieranController k;
        Traversal t;

        GameObject Box(Vector3 centre, Vector3 size, bool climbable = false)
        {
            var b = GameObject.CreatePrimitive(PrimitiveType.Cube);
            b.transform.SetParent(root.transform);
            b.transform.position = centre;
            b.transform.localScale = size;
            if (climbable) b.AddComponent<Climbable>();
            return b;
        }

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            root = new GameObject("range");
            Box(new Vector3(0f, -0.5f, 0f), new Vector3(100f, 1f, 100f));
            kieranGo = new GameObject("Kieran");
            var cc = kieranGo.AddComponent<CharacterController>();
            cc.height = 1.76f; cc.radius = 0.34f; cc.center = new Vector3(0f, 0.88f, 0f);
            k = kieranGo.AddComponent<KieranController>();
            t = kieranGo.AddComponent<Traversal>();
            k.Teleport(new Vector3(0f, 0.1f, 0f), 0f);
            yield return new WaitForSeconds(0.2f);
        }

        [UnityTearDown]
        public IEnumerator TearDown()
        {
            Object.Destroy(kieranGo); Object.Destroy(root);
            yield return null;
        }

        [UnityTest]
        public IEnumerator MantlesAChestHighWall()
        {
            Box(new Vector3(0f, 0.6f, 3f), new Vector3(4f, 1.2f, 2f));   // 1.2 m wall, top at z 2..4
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            bool mantled = false;
            for (float s = 0f; s < 3f && !(mantled && t.State == TraversalState.None); s += Time.deltaTime)
            {
                mantled |= t.State == TraversalState.Mantling;
                yield return null;
            }
            k.Input.ScriptedMove = Vector2.zero;
            yield return new WaitForSeconds(0.3f);
            Assert.IsTrue(mantled);
            Assert.AreEqual(1.2f, k.transform.position.y, 0.1f, "standing on top");
        }

        [UnityTest]
        public IEnumerator GrabsALedgeWhenFallingPastIt()
        {
            Box(new Vector3(0f, 3f, 3f), new Vector3(4f, 6f, 2f));        // 6 m wall
            k.Teleport(new Vector3(0f, 4.5f, 1.55f), 0f);                 // falling, facing the wall, ledge 1.5 m above the feet
            yield return new WaitForSeconds(0.25f);
            // The ledge passes into hang range as Kieran falls.
            bool hung = false;
            for (float s = 0f; s < 1f && !hung; s += Time.deltaTime) { hung = t.State == TraversalState.Hanging || t.State == TraversalState.Mantling; yield return null; }
            Assert.IsTrue(hung, "caught the ledge");
            k.JumpPressed();
            yield return new WaitForSeconds(1f);
            Assert.AreEqual(6f, k.transform.position.y, 0.15f, "pulled up onto the top");
        }

        [UnityTest]
        public IEnumerator ClimbsAClimbableWallToTheTop()
        {
            Box(new Vector3(0f, 2.5f, 3f), new Vector3(4f, 5f, 2f), climbable: true);   // 5 m climbable wall
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            bool climbed = false;
            for (float s = 0f; s < 8f && k.transform.position.y < 4.9f; s += Time.deltaTime) { climbed |= t.State == TraversalState.Climbing; yield return null; }
            k.Input.ScriptedMove = Vector2.zero;
            yield return new WaitForSeconds(0.6f);
            Assert.IsTrue(climbed);
            Assert.AreEqual(5f, k.transform.position.y, 0.15f, "climbed and mantled onto the top");
        }

        [UnityTest]
        public IEnumerator PlainWallsAreNotClimbable()
        {
            Box(new Vector3(0f, 2.5f, 3f), new Vector3(4f, 5f, 2f));
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            yield return new WaitForSeconds(2f);
            Assert.AreEqual(TraversalState.None, t.State);
            Assert.Less(k.transform.position.y, 0.2f);
        }
    }
}

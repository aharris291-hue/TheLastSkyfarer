// The Last Skyfarer: Kieran's movement in play mode, on a generated test ground with a capsule stand-in.
using System.Collections;
using LastSkyfarer.Player;
using LastSkyfarer.World;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace LastSkyfarer.Tests
{
    public class KieranMovementTests
    {
        GameObject ground, cliff, kieranGo;
        KieranController k;

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            ground = GameObject.CreatePrimitive(PrimitiveType.Cube);
            ground.transform.localScale = new Vector3(1200f, 1f, 1200f);
            ground.transform.position = new Vector3(0f, -0.5f, 0f);
            cliff = GameObject.CreatePrimitive(PrimitiveType.Cube);   // a 40 m tower to glide off
            cliff.transform.localScale = new Vector3(10f, 40f, 10f);
            cliff.transform.position = new Vector3(0f, 20f, -60f);
            kieranGo = new GameObject("Kieran");
            var cc = kieranGo.AddComponent<CharacterController>();
            cc.height = 1.76f; cc.radius = 0.34f; cc.center = new Vector3(0f, 0.88f, 0f);
            k = kieranGo.AddComponent<KieranController>();
            k.Teleport(new Vector3(0f, 0.1f, 0f), 0f);
            yield return new WaitForSeconds(0.3f);
        }

        [UnityTearDown]
        public IEnumerator TearDown()
        {
            Object.Destroy(kieranGo); Object.Destroy(ground); Object.Destroy(cliff);
            foreach (var w in Object.FindObjectsByType<WindVolume>(FindObjectsSortMode.None)) Object.Destroy(w.gameObject);
            yield return null;
        }

        [UnityTest]
        public IEnumerator RunsAtRunSpeed()
        {
            Assert.AreEqual(MoveMode.Grounded, k.Mode);
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            yield return new WaitForSeconds(1.5f);
            float z0 = k.transform.position.z;
            yield return new WaitForSeconds(1f);
            Assert.AreEqual(k.RunSpeed, k.transform.position.z - z0, 0.4f);
        }

        [UnityTest]
        public IEnumerator JumpsAboutJumpHeight()
        {
            k.JumpPressed();
            float top = 0f;
            for (float t = 0f; t < 1.2f; t += Time.deltaTime) { top = Mathf.Max(top, k.transform.position.y); yield return null; }
            Assert.AreEqual(k.JumpHeight, top, 0.2f);
            Assert.AreEqual(MoveMode.Grounded, k.Mode, "lands again");
        }

        [UnityTest]
        public IEnumerator GlidesOffTheCliffAndLands()
        {
            k.Teleport(new Vector3(0f, 40.2f, -60f), 0f);
            yield return new WaitForSeconds(0.3f);
            k.Input.ScriptedMove = new Vector2(0f, 1f);
            yield return new WaitForSeconds(1.6f);   // runs off the 5 m wide top
            Assert.AreEqual(MoveMode.Falling, k.Mode);
            k.Input.ScriptedMove = Vector2.zero;
            Assert.IsTrue(k.TryDeploy(), "deploys in the air");
            float y0 = k.transform.position.y, z0 = k.transform.position.z;
            yield return new WaitForSeconds(3f);
            Assert.AreEqual(MoveMode.Gliding, k.Mode);
            float sink = (y0 - k.transform.position.y) / 3f, forward = (k.transform.position.z - z0) / 3f;
            Assert.Less(sink, 4f, "a glide, not a fall");
            Assert.Greater(forward, 8f);
            for (float t = 0f; t < 40f && k.Mode == MoveMode.Gliding; t += Time.deltaTime) yield return null;
            Assert.AreEqual(MoveMode.Grounded, k.Mode, "lands on the ground");
        }

        [UnityTest]
        public IEnumerator CurrentCarriesTheGliderWithoutSinking()
        {
            var w = new GameObject("current").AddComponent<WindVolume>();
            w.Points.Add(new Vector3(0f, 30f, -40f));
            w.Points.Add(new Vector3(0f, 30f, 100f));
            w.Radius = 8f; w.Strength = 12f;
            k.Teleport(new Vector3(0f, 30f, -30f), 0f);
            yield return null;
            Assert.IsTrue(k.TryDeploy());
            float y0 = k.transform.position.y;
            yield return new WaitForSeconds(2f);
            Assert.GreaterOrEqual(k.transform.position.y, y0 - 0.2f, "the current holds altitude");
        }

        [UnityTest]
        public IEnumerator FallingOffTheWorldReturnsToTheLastSafeLedge()
        {
            yield return new WaitForSeconds(2.2f);   // sample a safe point on the ground
            Vector3 safe = k.SafePoint;
            k.Teleport(new Vector3(500f, -195f, 500f), 0f);
            yield return new WaitForSeconds(3f);
            Assert.Less(Vector3.Distance(k.transform.position, safe), 2f);
        }
    }
}

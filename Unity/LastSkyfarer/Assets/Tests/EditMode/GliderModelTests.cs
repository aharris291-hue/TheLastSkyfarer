// The Last Skyfarer: glider flight model tests (ported from the Unreal automation tests).
using LastSkyfarer.Glider;
using LastSkyfarer.World;
using NUnit.Framework;
using UnityEngine;

namespace LastSkyfarer.Tests
{
    public class GliderModelTests
    {
        static readonly GliderParams P = new GliderParams();

        [Test]
        public void TrimFlightIsSteady()
        {
            var s = new GliderState { Speed = P.TrimSpeed, PathAngle = GliderModel.TrimPathAngle(P) };
            float sink = 0f;
            for (int i = 0; i < 600; i++) sink += GliderModel.Step(ref s, new GliderInput(), P, 1f / 60f).HeightDelta;
            Assert.AreEqual(P.TrimSpeed, s.Speed, 0.05f, "speed holds at trim");
            Assert.AreEqual(-P.TrimSinkRate * 10f, sink, 0.3f, "sinks at the trim rate for 10 s");
        }

        [Test]
        public void EnergyNeverRisesWithoutAssist([Values(1f / 30f, 1f / 60f, 0.1f)] float dt)
        {
            var s = new GliderState { Speed = 20f, PathAngle = 0f };
            float h = 0f, e0 = GliderModel.SpecificEnergy(s.Speed, h, P);
            for (int i = 0; i < 400; i++)
            {
                float pitch = Mathf.Sin(i * 0.05f);
                h += GliderModel.Step(ref s, new GliderInput { Pitch = pitch, Turn = 0.3f }, P, dt).HeightDelta;
                float e = GliderModel.SpecificEnergy(s.Speed, h, P);
                Assert.LessOrEqual(e, e0 + 1e-3f);
                e0 = e;
            }
        }

        [Test]
        public void DivingGainsSpeedAndPullingUpClimbs()
        {
            var s = new GliderState { Speed = P.TrimSpeed, PathAngle = GliderModel.TrimPathAngle(P) };
            for (int i = 0; i < 180; i++) GliderModel.Step(ref s, new GliderInput { Pitch = 1f }, P, 1f / 60f);
            Assert.Greater(s.Speed, P.TrimSpeed + 5f);
            for (int i = 0; i < 60; i++) GliderModel.Step(ref s, new GliderInput { Pitch = -1f }, P, 1f / 60f);   // nose comes up
            float climb = 0f;
            for (int i = 0; i < 30; i++) climb += GliderModel.Step(ref s, new GliderInput { Pitch = -1f }, P, 1f / 60f).HeightDelta;
            Assert.Greater(climb, 0f, "climbing on the speed gained in the dive");
        }

        [Test]
        public void SlowFlightStallsAndRecovers()
        {
            var s = new GliderState { Speed = 6f, PathAngle = 0f };
            GliderModel.Step(ref s, new GliderInput(), P, 1f / 60f);
            Assert.IsTrue(s.Stalled);
            for (int i = 0; i < 300 && s.Stalled; i++) GliderModel.Step(ref s, new GliderInput(), P, 1f / 60f);
            Assert.IsFalse(s.Stalled);
        }

        [Test]
        public void TurnsSlowerWhenFaster()
        {
            Assert.Greater(GliderModel.TurnRate(10f, P), GliderModel.TurnRate(30f, P));
            Assert.GreaterOrEqual(GliderModel.TurnRate(100f, P), P.MinTurnRate);
        }

        [Test]
        public void HeadingFollowsVelocity()
        {
            Assert.AreEqual(90f, GliderModel.FromVelocity(new Vector3(10f, 0f, 0f), P).Yaw, 0.01f);
            Assert.AreEqual(0f, GliderModel.FromVelocity(new Vector3(0f, -3f, 8f), P).Yaw, 0.01f);
            Assert.AreEqual(P.StallRecoverSpeed, GliderModel.FromVelocity(Vector3.zero, P).Speed, 0.01f);
        }

        [Test]
        public void RollLandingAboveSafeSpeed()
        {
            Assert.IsFalse(GliderModel.IsRollLanding(P.SafeLandingSpeed - 1f, P));
            Assert.IsTrue(GliderModel.IsRollLanding(P.SafeLandingSpeed + 1f, P));
        }

        [Test]
        public void SafePointsSampleOnStableGroundOnly()
        {
            var t = new SafePointTracker { SampleInterval = 2f };
            t.Update(0, Vector3.one, false);
            Assert.IsFalse(t.HasSafePoint);
            t.Update(0, Vector3.one, true);
            t.Update(1, Vector3.zero, true);
            Assert.AreEqual(Vector3.one, t.SafePoint, "not resampled before the interval");
            t.Update(2.5, Vector3.zero, true);
            Assert.AreEqual(Vector3.zero, t.SafePoint);
        }

        [Test]
        public void WindCurrentPushesAlongAndHoldsAltitude()
        {
            var go = new GameObject("wind");
            var w = go.AddComponent<WindVolume>();
            w.Points.Add(Vector3.zero);
            w.Points.Add(new Vector3(0f, 0f, 100f));
            w.Radius = 6f;
            w.Strength = 10f;
            var s = w.Sample(new Vector3(0f, 0f, 50f));
            Assert.IsTrue(s.Inside && s.HoldAltitude);
            Assert.AreEqual(10f, s.Velocity.z, 0.01f);
            Assert.IsFalse(w.Sample(new Vector3(20f, 0f, 50f)).Inside, "outside the radius");
            Assert.IsFalse(w.Sample(new Vector3(0f, 0f, 120f)).Inside, "past the end");
            w.StartsHidden = true;
            Assert.IsFalse(w.Sample(new Vector3(0f, 0f, 50f)).Inside, "hidden until revealed");
            w.Reveal();
            Assert.IsTrue(w.Sample(new Vector3(0f, 0f, 50f)).Inside);
            Object.DestroyImmediate(go);
        }
    }
}

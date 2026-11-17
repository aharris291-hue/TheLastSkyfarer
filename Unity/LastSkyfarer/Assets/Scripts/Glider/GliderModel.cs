// The Last Skyfarer: pure glider flight model (GDD 2.1), ported from the Unreal version unchanged.
// No engine state, so it can be unit tested. Speeds in m/s, angles in degrees, Unity axes (Y up, Z forward at yaw 0).
using System;
using UnityEngine;

namespace LastSkyfarer.Glider
{
    [Serializable]
    public class GliderParams
    {
        [Tooltip("Neutral glide speed, m/s.")] public float TrimSpeed = 14f;
        [Tooltip("Sink rate at trim speed with no pitch input, m/s.")] public float TrimSinkRate = 1.6f;
        [Tooltip("Speed cap in a dive, m/s.")] public float MaxDiveSpeed = 32f;
        [Tooltip("Below this the glider stalls and noses down.")] public float StallSpeed = 7f;
        [Tooltip("Stall ends once speed is back above this.")] public float StallRecoverSpeed = 9f;
        [Tooltip("Share of kinetic energy turned into height when pulling up.")] [Range(0.05f, 1f)] public float PullUpEfficiency = 0.7f;
        [Tooltip("Extra deceleration while the air brake is held, m/s².")] public float AirBrakeDecel = 6f;
        public float MaxDiveAngle = 45f;
        public float MaxClimbAngle = 30f;
        [Tooltip("Nose-down angle while stalled.")] public float StallNoseDownAngle = 30f;
        [Tooltip("How fast the flight-path angle follows the stick, deg/s.")] public float PitchRate = 90f;
        [Tooltip("Turn rate at trim speed; it falls as speed rises, deg/s.")] public float TurnRateAtTrim = 60f;
        public float MinTurnRate = 18f;
        [Tooltip("Touching ground below this folds the glider into a run; above it is a roll landing.")] public float SafeLandingSpeed = 18f;
        public float Gravity = 9.81f;
    }

    [Serializable]
    public struct GliderState
    {
        public float Speed;      // airspeed along the flight path, m/s
        public float PathAngle;  // degrees, negative = descending
        public float Yaw;        // heading, degrees (0 = +Z, 90 = +X)
        public bool Stalled;
    }

    public struct GliderInput
    {
        public float Pitch;      // +1 = stick forward (dive), -1 = stick back (pull up)
        public float Turn;       // -1 left .. +1 right
        public bool AirBrake;
        public bool Assist;      // accessibility: holds altitude when there is no pitch input
    }

    public struct GliderStepResult
    {
        public Vector3 AirDisplacement;   // metres through the air this step; wind is added by the caller
        public float HeightDelta;
    }

    public static class GliderModel
    {
        public static float TrimPathAngle(GliderParams p)
        {
            float sinG = Mathf.Clamp(p.TrimSinkRate / Mathf.Max(p.TrimSpeed, 0.1f), 0f, 0.99f);
            return -Mathf.Asin(sinG) * Mathf.Rad2Deg;
        }

        /// <summary>Linear drag constant (per second) chosen so trim flight is steady.</summary>
        public static float DragCoefficient(GliderParams p)
        {
            float sinG = Mathf.Clamp(p.TrimSinkRate / Mathf.Max(p.TrimSpeed, 0.1f), 0f, 0.99f);
            return p.Gravity * sinG / Mathf.Max(p.TrimSpeed, 0.1f);
        }

        /// <summary>Starts a glide from the current velocity (m/s, world axes).</summary>
        public static GliderState FromVelocity(Vector3 velocity, GliderParams p, float fallbackYaw = 0f)
        {
            var horizontal = new Vector3(velocity.x, 0f, velocity.z);
            return new GliderState
            {
                Yaw = horizontal.sqrMagnitude < 0.01f ? fallbackYaw : Mathf.Atan2(horizontal.x, horizontal.z) * Mathf.Rad2Deg,
                // Deploying keeps forward momentum but never starts slower than a gentle stall recovery.
                Speed = Mathf.Clamp(horizontal.magnitude, p.StallRecoverSpeed, p.MaxDiveSpeed),
                PathAngle = TrimPathAngle(p),
                Stalled = false,
            };
        }

        public static float TurnRate(float speed, GliderParams p)
        {
            float scaled = p.TurnRateAtTrim * p.TrimSpeed / Mathf.Max(speed, 1f);
            return Mathf.Clamp(scaled, p.MinTurnRate, p.TurnRateAtTrim * 1.5f);
        }

        public static float SpecificEnergy(float speed, float height, GliderParams p) => p.Gravity * height + 0.5f * speed * speed;

        public static bool IsRollLanding(float impactSpeed, GliderParams p) => impactSpeed > p.SafeLandingSpeed;

        /// <summary>
        /// Advances one step. Height uses the average of old and new speed, so without the assist the specific energy
        /// (g*h + v^2/2) can never rise, whatever the step size.
        /// </summary>
        public static GliderStepResult Step(ref GliderState s, GliderInput input, GliderParams p, float dt)
        {
            var result = new GliderStepResult();
            if (dt <= 0f) return result;

            float pitch = Mathf.Clamp(input.Pitch, -1f, 1f);
            bool assistHold = input.Assist && Mathf.Abs(pitch) < 0.1f;
            float trim = TrimPathAngle(p);

            if (s.Speed < p.StallSpeed) s.Stalled = true;
            else if (s.Stalled && s.Speed >= p.StallRecoverSpeed) s.Stalled = false;

            float target;
            if (s.Stalled) target = -p.StallNoseDownAngle;
            else if (assistHold) target = 0f;
            else if (pitch >= 0f) target = Mathf.Lerp(trim, -p.MaxDiveAngle, pitch);
            else target = Mathf.Lerp(trim, p.MaxClimbAngle, -pitch);
            s.PathAngle = Mathf.MoveTowards(s.PathAngle, target, p.PitchRate * dt);

            float sinG = Mathf.Sin(s.PathAngle * Mathf.Deg2Rad);
            float cosG = Mathf.Cos(s.PathAngle * Mathf.Deg2Rad);

            // Diving converts height to speed one to one; climbing pays 1/PullUpEfficiency in speed per unit of height.
            float accel = -DragCoefficient(p) * s.Speed;
            accel += sinG < 0f ? -p.Gravity * sinG : -p.Gravity * sinG / Mathf.Max(p.PullUpEfficiency, 0.05f);
            if (input.AirBrake) accel -= p.AirBrakeDecel;
            if (assistHold && !input.AirBrake) accel = (p.TrimSpeed - s.Speed) * 0.8f;   // accessibility, not energy-conserving

            float oldSpeed = s.Speed;
            float newSpeed = Mathf.Clamp(oldSpeed + accel * dt, 0.5f, p.MaxDiveSpeed);
            s.Speed = newSpeed;

            float avg = 0.5f * (oldSpeed + newSpeed);
            s.Yaw = Mathf.Repeat(s.Yaw + Mathf.Clamp(input.Turn, -1f, 1f) * TurnRate(avg, p) * dt + 180f, 360f) - 180f;

            float yawRad = s.Yaw * Mathf.Deg2Rad;
            float horizontal = avg * cosG * dt;
            result.HeightDelta = avg * sinG * dt;
            result.AirDisplacement = new Vector3(horizontal * Mathf.Sin(yawRad), result.HeightDelta, horizontal * Mathf.Cos(yawRad));
            return result;
        }
    }

    /// <summary>Remembers the last stable ground position, sampled at a fixed interval (GDD 2.5).</summary>
    public class SafePointTracker
    {
        public float SampleInterval = 2f;
        public double LastSampleTime = -1e9;
        public Vector3 SafePoint;
        public bool HasSafePoint;

        public void Update(double now, Vector3 location, bool onStableGround)
        {
            if (onStableGround && (!HasSafePoint || now - LastSampleTime >= SampleInterval))
            {
                SafePoint = location;
                LastSampleTime = now;
                HasSafePoint = true;
            }
        }
    }
}

// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>Turns about its local X axis (the windmill sails).</summary>
    public class Spinner : MonoBehaviour
    {
        public float DegreesPerSecond = 25f;
        void Update() => transform.Rotate(Vector3.right, DegreesPerSecond * Time.deltaTime, Space.Self);
    }
}

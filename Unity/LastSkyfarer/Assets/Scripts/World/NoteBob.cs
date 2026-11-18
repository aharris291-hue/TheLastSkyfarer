// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>A notes page bobs and turns gently until it is picked up.</summary>
    public class NoteBob : MonoBehaviour
    {
        Vector3 basePos;
        void Start() => basePos = transform.localPosition;
        void Update()
        {
            transform.localPosition = basePos + Vector3.up * (Mathf.Sin(Time.time * 2f) * 0.08f);
            transform.Rotate(Vector3.up, 40f * Time.deltaTime, Space.World);
        }
    }
}

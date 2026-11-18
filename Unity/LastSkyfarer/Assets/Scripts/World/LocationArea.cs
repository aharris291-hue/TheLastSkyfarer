// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>Entering it discovers the place (and shows its name).</summary>
    [RequireComponent(typeof(BoxCollider))]
    public class LocationArea : MonoBehaviour
    {
        public string LocationId;
        void OnTriggerEnter(Collider c) { if (StoryWorldUtil.IsKieran(c)) StoryManager.Instance.DiscoverLocation(LocationId); }
    }
}

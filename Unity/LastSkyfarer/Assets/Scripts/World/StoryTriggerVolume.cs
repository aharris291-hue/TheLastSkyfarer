// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>Fires its Interactions.json trigger once when Kieran walks in (retries while a conversation is running).</summary>
    [RequireComponent(typeof(BoxCollider))]
    public class StoryTriggerVolume : MonoBehaviour
    {
        public string TriggerId;
        bool inside;
        void OnTriggerEnter(Collider c) { if (StoryWorldUtil.IsKieran(c)) { inside = true; TryFire(); } }
        void OnTriggerExit(Collider c) { if (StoryWorldUtil.IsKieran(c)) inside = false; }
        void Update() { if (inside) TryFire(); }
        void TryFire()
        {
            var story = StoryManager.Instance;
            var def = story.Database.FindTrigger(TriggerId);
            if (def == null || story.HasFlag(def.OnceFlag)) { inside = false; return; }
            if (story.TryFire(def)) inside = false;
        }
    }
}

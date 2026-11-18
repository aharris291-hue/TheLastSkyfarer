// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>Shows its renderers and/or enables its colliders only while the story conditions hold.</summary>
    public class ConditionalObject : MonoBehaviour
    {
        public List<string> ShowIf = new List<string>();
        public bool AffectRenderers = true, AffectColliders = true;

        void OnEnable() { StoryManager.Instance.OnFlagChanged += Changed; Refresh(); }
        void OnDisable() => StoryManager.Instance.OnFlagChanged -= Changed;
        void Changed(string flag, bool set) => Refresh();
        void Start() => Refresh();

        public void Refresh()
        {
            bool on = StoryManager.Instance.CheckAll(ShowIf);
            if (AffectRenderers) foreach (var r in GetComponentsInChildren<Renderer>(true)) r.enabled = on;
            if (AffectColliders) foreach (var c in GetComponentsInChildren<Collider>(true)) c.enabled = on;
        }
    }
}

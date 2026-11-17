// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>Kieran's interact button: talk/inspect/pick up the nearest available thing, or read on in a conversation.</summary>
    [RequireComponent(typeof(KieranController))]
    public class KieranInteractor : MonoBehaviour
    {
        KieranController k;
        public Interactable Focus { get; private set; }

        void Awake() => k = GetComponent<KieranController>();

        void Update()
        {
            var story = StoryManager.Instance;
            Focus = story.IsInDialogue ? null : FindFocus();
            if (!k.Input.Interact.WasPressedThisFrame()) return;
            if (story.IsInDialogue) story.AdvanceDialogue();
            else if (Focus) Focus.Use(transform.position);
        }

        Interactable FindFocus()
        {
            Interactable best = null;
            float bestScore = float.MaxValue;
            Vector3 p = transform.position + Vector3.up * 0.9f;
            foreach (var it in Interactable.All)
            {
                if (it.Def == null) continue;
                float d = Vector3.Distance(p, it.transform.position);
                if (d > it.Def.Radius + 0.5f || !it.Available) continue;
                Vector3 to = it.transform.position - transform.position; to.y = 0f;
                float facing = to.sqrMagnitude > 0.01f ? Vector3.Dot(transform.forward, to.normalized) : 1f;
                float score = d - facing;              // prefer what he is facing
                if (score < bestScore) { bestScore = score; best = it; }
            }
            return best;
        }
    }
}

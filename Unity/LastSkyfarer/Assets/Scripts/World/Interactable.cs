// The Last Skyfarer: the level's story pieces (ports of ALSStoryTrigger, ALSLocationVolume, ALSStoryNPC/ALSInspectable/
// ALSJournalPickup and ALSSpinningMesh). Their rules live in Resources/Story/Interactions.json; these components only
// connect a place in the world to them.
using System.Collections.Generic;
using LastSkyfarer.Player;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    /// <summary>A villager, something to inspect, or one of Elias's notes. Kieran's interactor uses the nearest one.</summary>
    public class Interactable : MonoBehaviour
    {
        public static readonly List<Interactable> All = new List<Interactable>();
        public string InteractableId;
        public InteractableDef Def { get; private set; }
        public Transform FaceKieran;      // a villager's body turns towards Kieran when spoken to

        void Awake() => Def = StoryManager.Instance.Database.FindInteractable(InteractableId);
        void OnEnable() => All.Add(this);
        void OnDisable() => All.Remove(this);

        public bool Available => Def != null && StoryManager.Instance.CanInteract(Def);

        public bool Use(Vector3 from)
        {
            if (Def == null || !StoryManager.Instance.Interact(Def)) return false;
            if (FaceKieran)
            {
                Vector3 d = from - FaceKieran.position; d.y = 0f;
                if (d.sqrMagnitude > 0.01f) FaceKieran.rotation = Quaternion.LookRotation(d);
            }
            return true;
        }
    }
}

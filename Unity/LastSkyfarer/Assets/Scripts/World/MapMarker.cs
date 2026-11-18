// The Last Skyfarer: a place or objective on Brindle Isle's map (ALSMapMarkerActor). The map screen arrives in U6.
using UnityEngine;

namespace LastSkyfarer.World
{
    public class MapMarker : MonoBehaviour
    {
        public string Kind = "landmark";       // landmark, objective
        public string LocationId = "";
        public string Quest = "", Objective = "";
    }
}

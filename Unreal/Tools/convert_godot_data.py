#!/usr/bin/env python3
"""Convert the archived Godot demo's JSON data (data/) into the Unreal build's
narrative data (Unreal/Content/LastSkyfarer/Data/).

The Godot files are read only, never changed. Wording is copied verbatim; the
only exceptions are listed in TEXT_OVERRIDES, each tied to an approved decision.

Usage: python3 Unreal/Tools/convert_godot_data.py            (write files)
       python3 Unreal/Tools/convert_godot_data.py --check    (exit 1 if out of date)
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "data")
DST = os.path.join(ROOT, "Unreal", "Content", "LastSkyfarer", "Data")

# (conversation, line index, old text, new text, reason). Narrator lines only;
# canon lines are never overridden.
EXTRA_LOCATIONS = [
    {"Id": "central_square", "Name": "Central Square", "Subtitle": "Windrest Village"},
    {"Id": "orchard_vale", "Name": "Orchard Vale", "Subtitle": "Brindle Isle"},
]

TEXT_OVERRIDES = [
    ("opening", 0, "Old Cartographer's Bluff, Brindle Isle. Sunrise.",
     "Upper Cliffs, Brindle Isle. Sunrise.",
     "D-15: the game opens on the Upper Cliffs at sunrise"),
]

ACTION_TYPES = {
    "set": "SetFlag", "clear": "ClearFlag", "give": "GiveItem", "take": "TakeItem",
    "quest_start": "StartQuest", "objective": "AdvanceObjective",
    "quest_complete": "CompleteQuest", "journal": "AddJournal", "event": "Event",
    "time": "TimeOfDay", "chapter": "Chapter", "autosave": "Autosave", "sfx": "Sfx",
}
# Story events whose consequences lived in Godot level scripts (workshop.gd
# "next_morning", level.gd Elias note pickups). Data-driven here so levels only
# fire the event. Each entry: event -> actions, same shape as dialogue actions.
EVENT_ACTIONS = {
    "next_morning": [{"Type": "Chapter", "Arg": "", "Amount": 3},
                     {"Type": "TimeOfDay", "Arg": "Dawn", "Amount": 1},
                     {"Type": "StartQuest", "Arg": "into_the_clouds", "Amount": 1}],
}
# Journal collectible groups that advance a quest objective when an entry is added.
COLLECTIBLE_OBJECTIVES = {"elias_notes": "elias_was_here:notes"}

# Godot used "day" for the restored daylight preset after the night scenes.
TIME_NAMES = {"day": "Morning"}


def load(name):
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        return json.load(f)


def convert_actions(step):
    out = []
    for a in step.get("do", []):
        amount = int(a.get("n", 1))
        for key, val in a.items():
            if key == "n":
                continue
            if key not in ACTION_TYPES:
                raise SystemExit(f"Unknown action {key!r}")
            t = ACTION_TYPES[key]
            if t == "Chapter":
                out.append({"Type": t, "Arg": "", "Amount": int(val)})
            elif t == "Autosave":
                out.append({"Type": t, "Arg": "", "Amount": 1})
            elif t == "TimeOfDay":
                out.append({"Type": t, "Arg": TIME_NAMES.get(val, str(val).capitalize()), "Amount": 1})
            else:
                out.append({"Type": t, "Arg": str(val), "Amount": amount})
    return out


def build():
    overrides = {(c, i): (old, new) for c, i, old, new, _ in TEXT_OVERRIDES}
    conversations = []
    for fname in ("windrest", "workshop", "sky"):
        for conv_id, steps in load(f"dialogue/{fname}.json").items():
            lines = []
            for i, st in enumerate(steps):
                text = st.get("t", "")
                if (conv_id, i) in overrides:
                    old, new = overrides[(conv_id, i)]
                    if text != old:
                        raise SystemExit(f"Override for {conv_id}[{i}] no longer matches: {text!r}")
                    if st.get("canon"):
                        raise SystemExit(f"Refusing to override canon line {conv_id}[{i}]")
                    text = new
                lines.append({
                    "Speaker": st.get("s", ""),
                    "Emotion": st.get("p", ""),
                    "Text": text,
                    "bCanon": bool(st.get("canon", False)),
                    "VoiceKey": f"{conv_id}.{i:02d}" if text and st.get("s") not in ("", "narrator") else "",
                    "Actions": convert_actions(st),
                })
            conversations.append({"Id": conv_id, "Source": f"data/dialogue/{fname}.json", "Lines": lines})

    def hidden(v):
        if v is None:
            return []
        return v if isinstance(v, list) else [v]

    quests = []
    for qid, q in load("quests.json").items():
        quests.append({
            "Id": qid, "Title": q["title"], "Chapter": q.get("chapter", 1), "bMain": q.get("main", False),
            "Description": q.get("desc", ""), "bAutoComplete": q.get("auto_complete", False),
            "TurnIn": q.get("turn_in", ""), "Rewards": q.get("rewards", []),
            "Objectives": [{"Id": o["id"], "Text": o["text"], "Count": o.get("count", 1),
                            "bOptional": o.get("optional", False),
                            "HiddenUntil": hidden(o.get("hidden_until"))} for o in q["objectives"]],
        })
    journal = [{"Id": k, "Title": v["title"], "Kind": v.get("kind", "story"),
                "Collectible": v.get("collectible", ""), "bCanon": v.get("canon", False),
                "Text": v["text"], "Source": v.get("source", "")} for k, v in load("journal.json").items()]
    items = [{"Id": k, "Name": v["name"], "Category": v.get("category", ""), "Description": v.get("desc", "")}
             for k, v in load("items.json").items()]
    speakers = [{"Id": k, "DisplayName": v.get("name", ""), "Portrait": v.get("portrait", ""),
                 "DefaultEmotion": v.get("default", ""), "Color": v.get("color", "")}
                for k, v in load("speakers.json").items()]
    locations = [{"Id": k, "Name": v["name"], "Subtitle": v.get("subtitle", "")}
                 for k, v in load("locations.json").items()]
    # Milestone A places added for the 3D island (VERTICAL_SLICE.md); not in the Godot demo.
    known = {l["Id"] for l in locations}
    locations += [l for l in EXTRA_LOCATIONS if l["Id"] not in known]
    events = [{"Id": k, "Actions": v} for k, v in EVENT_ACTIONS.items()]
    collect = [{"Group": k, "Objective": v} for k, v in COLLECTIBLE_OBJECTIVES.items()]
    header = "Generated by Unreal/Tools/convert_godot_data.py from the archived Godot demo. Edit the generator or these files, never data/."
    return {
        "Conversations.json": {"Note": header, "Conversations": conversations},
        "Quests.json": {"Note": header, "Quests": quests},
        "Journal.json": {"Note": header, "Entries": journal},
        "Items.json": {"Note": header, "Items": items},
        "Speakers.json": {"Note": header, "Speakers": speakers},
        "Locations.json": {"Note": header, "Locations": locations},
        "StoryEvents.json": {"Note": header, "Events": events, "CollectibleObjectives": collect},
    }


def main():
    files = build()
    check = "--check" in sys.argv
    os.makedirs(DST, exist_ok=True)
    stale = []
    for name, data in files.items():
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        path = os.path.join(DST, name)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old != text:
            stale.append(name)
            if not check:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
    if check and stale:
        print("Out of date:", ", ".join(stale))
        sys.exit(1)
    print(("Up to date" if check else "Wrote") + f": {len(files)} files in {os.path.relpath(DST, ROOT)}")


if __name__ == "__main__":
    main()

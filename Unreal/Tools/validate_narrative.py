#!/usr/bin/env python3
"""Checks the Unreal narrative data without the engine: every reference resolves,
canon lines match the Godot source word for word, and a simulated Milestone A
run (conversations in story order plus world triggers) completes every quest.
Mirrors the C++ automation test LastSkyfarer.Narrative.*. Exit code 1 on failure."""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(ROOT, "Unreal", "Content", "LastSkyfarer", "Data")
J = lambda n: json.load(open(os.path.join(D, n), encoding="utf-8"))
convs = {c["Id"]: c for c in J("Conversations.json")["Conversations"]}
quests = {q["Id"]: q for q in J("Quests.json")["Quests"]}
journal = {e["Id"]: e for e in J("Journal.json")["Entries"]}
items = {i["Id"]: i for i in J("Items.json")["Items"]}
speakers = {s["Id"] for s in J("Speakers.json")["Speakers"]}
ev = J("StoryEvents.json")
events = {e["Id"]: e["Actions"] for e in ev["Events"]}
collect = {c["Group"]: c["Objective"] for c in ev["CollectibleObjectives"]}
errors = []

# 1. References
for cid, c in convs.items():
    for i, ln in enumerate(c["Lines"]):
        if ln["Text"] and ln["Speaker"] not in speakers:
            errors.append(f"{cid}[{i}] unknown speaker {ln['Speaker']}")
        for a in ln["Actions"]:
            t, arg = a["Type"], a["Arg"]
            if t in ("StartQuest", "CompleteQuest") and arg not in quests:
                errors.append(f"{cid}[{i}] unknown quest {arg}")
            if t == "AdvanceObjective":
                q, _, o = arg.partition(":")
                if q not in quests or o not in {x["Id"] for x in quests[q]["Objectives"]}:
                    errors.append(f"{cid}[{i}] unknown objective {arg}")
            if t in ("GiveItem", "TakeItem") and arg not in items:
                errors.append(f"{cid}[{i}] unknown item {arg}")
            if t == "AddJournal" and arg not in journal:
                errors.append(f"{cid}[{i}] unknown journal entry {arg}")
for q in quests.values():
    for r in q["Rewards"]:
        if r not in items:
            errors.append(f"quest {q['Id']} unknown reward {r}")

# 2. Canon lines identical to the Godot source
for fname in ("windrest", "workshop", "sky"):
    src = json.load(open(os.path.join(ROOT, "data", "dialogue", f"{fname}.json"), encoding="utf-8"))
    for cid, steps in src.items():
        for i, st in enumerate(steps):
            if st.get("canon") and convs[cid]["Lines"][i]["Text"] != st["t"]:
                errors.append(f"canon line changed: {cid}[{i}]")

for e, acts in events.items():
    for a in acts:
        if a["Type"] == "StartQuest" and a["Arg"] not in quests: errors.append(f"event {e} unknown quest")
for g, o in collect.items():
    q, _, oid = o.partition(":")
    if q not in quests or oid not in {x["Id"] for x in quests[q]["Objectives"]}: errors.append(f"collectible {g} bad objective")
    if not any(j["Collectible"] == g for j in journal.values()): errors.append(f"collectible group {g} has no entries")

# 3. Simulated Milestone A run
state = {"flags": set(), "inv": {}, "q": {}, "journal": []}
def obj_done(q, o):
    if state["q"].get(q, {}).get("state") == "complete":
        return True
    need = next(x["Count"] for x in quests[q]["Objectives"] if x["Id"] == o)
    return state["q"].get(q, {}).get("obj", {}).get(o, 0) >= need
def run(actions):
    for a in actions:
        t, arg, n = a["Type"], a["Arg"], a["Amount"]
        if t == "SetFlag": state["flags"].add(arg)
        elif t == "GiveItem": state["inv"][arg] = state["inv"].get(arg, 0) + n
        elif t == "TakeItem":
            if state["inv"].get(arg, 0) < n: errors.append(f"take {arg} without having it")
            else: state["inv"][arg] -= n
        elif t == "StartQuest": state["q"].setdefault(arg, {"state": "active", "obj": {}})
        elif t == "AdvanceObjective":
            q, _, o = arg.partition(":")
            if state["q"].get(q, {}).get("state") != "active":
                errors.append(f"objective {arg} on inactive quest"); continue
            need = next(x["Count"] for x in quests[q]["Objectives"] if x["Id"] == o)
            state["q"][q]["obj"][o] = min(state["q"][q]["obj"].get(o, 0) + n, need)
            if quests[q]["bAutoComplete"] and all(obj_done(q, x["Id"]) for x in quests[q]["Objectives"] if not x["bOptional"]):
                run([{"Type": "CompleteQuest", "Arg": q, "Amount": 1}])
        elif t == "CompleteQuest":
            if state["q"].get(arg, {}).get("state") == "active":
                state["q"][arg]["state"] = "complete"
                for r in quests[arg]["Rewards"]: state["inv"][r] = state["inv"].get(r, 0) + 1
        elif t == "AddJournal":
            if arg not in state["journal"]:
                state["journal"].append(arg)
                g = journal[arg]["Collectible"]
                if g in collect and state["q"].get(collect[g].partition(":")[0], {}).get("state") == "active":
                    run([{"Type": "AdvanceObjective", "Arg": collect[g], "Amount": 1}])
        elif t == "Event":
            run(events.get(arg, []))
def talk(cid):
    for ln in convs[cid]["Lines"]:
        run(ln["Actions"])
def trigger(*acts):
    run([{"Type": t, "Arg": a, "Amount": 1} for t, a in acts])

# World triggers below stand in for level trigger volumes and pickups (as in the Godot levels).
talk("opening")
talk("maren_intro")
for c in ("tavern_deliver", "tessa_deliver", "villager_deliver"): talk(c)
talk("maren_return")
talk("maren_deed")
for e in (e for e in journal.values() if e["Collectible"] == "elias_notes"):
    trigger(("AddJournal", e["Id"]))
talk("workshop_enter")
for c in ("inspect_maps", "inspect_sketches", "inspect_notes", "search_done", "compartment", "final_entry", "compass_awakens", "workshop_leave_night"):
    talk(c)
talk("piko_meeting"); talk("launch_ready"); talk("piko_found_wind"); talk("wind_refuses")

for q in quests:
    st = state["q"].get(q, {}).get("state")
    if st != "complete":
        missing = [o["Id"] for o in quests[q]["Objectives"] if not obj_done(q, o["Id"])] if st else "never started"
        errors.append(f"quest {q} not complete after the run ({missing})")
if "demo_complete" not in state["flags"]:
    errors.append("demo_complete flag not set")

lines = sum(len(c["Lines"]) for c in convs.values())
print(f"{len(convs)} conversations, {lines} lines, {len(quests)} quests, {len(journal)} journal entries, {len(items)} items")
if errors:
    print("FAILED:"); [print(" -", e) for e in errors]; sys.exit(1)
print("PASSED: references, canon lines, simulated Milestone A run")

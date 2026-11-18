"""Writes Resources/Story/Interactions.json: Brindle Isle's NPCs, inspectables, notes, story triggers and areas, from the
placements in Unreal/Tools/build_brindle_greybox.py (Unity axes, metres).  python Unity/Tools/layout/make_interactions.py
"""
import json, sys
# Unreal (X fwd, Y right, Z up) -> Unity (x right, y up, z fwd): (Y, Z, X)
def U(p): return {"x": float(p[1]), "y": float(p[2]), "z": float(p[0])}
def S(s): return {"x": float(s[1]), "y": float(s[2]), "z": float(s[0])}
def act(t, a, n=1): return {"Type": t, "Arg": a, "Amount": n}
def rule(cond, conv, repeat=False, set_flag=None, event=None):
    d = []
    if set_flag: d.append(act("SetFlag", set_flag))
    if event: d.append(act("Event", event))
    return {"If": cond, "Conversation": conv, "Do": d, "Repeat": repeat}
I = []
def npc(id, speaker, c, yaw, prompt, rules):
    I.append({"Id": id, "Kind": "npc", "Speaker": speaker, "Prompt": prompt, "Position": U(c), "Size": {"x": 0.0, "y": 0.0, "z": 0.0}, "Yaw": yaw, "Radius": 2.5, "AvailableIf": [], "Rules": rules, "JournalId": ""})
def inspect(id, c, size, prompt, rules, available_if=None, yaw=0.0):
    I.append({"Id": id, "Kind": "inspect", "Speaker": "", "Prompt": prompt, "Position": U(c), "Size": S(size), "Yaw": yaw, "Radius": 2.0 + max(size[0], size[1]) * 0.5,
              "AvailableIf": available_if or [], "Rules": rules, "JournalId": ""})
def note(jid, c):
    I.append({"Id": "Note_" + jid, "Kind": "note", "Speaker": "", "Prompt": "Pick up", "Position": U(c), "Size": {"x": 0.0, "y": 0.0, "z": 0.0}, "Yaw": 0.0, "Radius": 2.0, "AvailableIf": [], "Rules": [], "JournalId": jid})
T = []
def trigger(id, c, ext, once, conv, cond=None):
    T.append({"Id": id, "OnceFlag": once, "Conversation": conv, "Position": U(c), "Size": S([e * 2 for e in ext]), "Conditions": cond or [], "Actions": []})
A = []
def location(id, c, ext): A.append({"Id": id, "Position": U(c), "Size": S([e * 2 for e in ext])})

IX, IY = 0.0, -3000.0
# Elias's workshop interior (built away from the island; the door teleports Kieran in and out).
inspect("Inspect_WorkshopDoor_Inside", (IX - 6.9, IY, 1.2), (0.2, 1.6, 2.4), "Go outside", [rule(["compass_active"], "", event="leave"), rule([], "workshop_leave_night", True)])
inspect("Inspect_Maps", (IX + 3, IY, 0.95), (1.8, 2.6, 0.05), "Study the maps", [rule(["!searched_maps"], "inspect_maps")])
inspect("Inspect_Sketches", (IX + 3, IY + 4.9, 1.8), (2.0, 0.1, 1.4), "Look at the sketches", [rule(["!searched_sketches"], "inspect_sketches")])
inspect("Inspect_Notes", (IX - 3, IY - 4.3, 1.2), (3.6, 0.2, 2.2), "Read the weather logs", [rule(["!searched_notes"], "inspect_notes"), rule([], "inspect_shelf", True)])
inspect("Inspect_Portrait", (IX - 3, IY + 4.9, 2.0), (1.0, 0.1, 1.3), "Look at the portrait", [rule([], "inspect_portrait", True)])
inspect("Inspect_Instruments", (IX + 5.5, IY - 3.5, 0.8), (1.2, 1.2, 1.2), "Examine the instruments", [rule([], "inspect_instruments", True)])
inspect("Inspect_Floorboard", (IX, IY + 1.5, 0.03), (1.6, 1.0, 0.06), "Lift the floorboard",
        [rule(["!compartment_open"], "compartment"), rule(["compartment_open", "!compass_active"], "final_entry")], available_if=["obj:hidden_workshop:search"])
inspect("Inspect_Glider", (48, 664, 20.6), (2.2, 5.0, 0.15), "Approach", [rule(["compass_active", "!piko_joined"], "piko_meeting")], available_if=["compass_active"])
npc("NPC_Maren", "maren", (47, 62, 0), 225, "Talk to Maren", [
    rule(["!obj:morning_deliveries:report"], "maren_intro"),
    rule(["quest:morning_deliveries:active", "obj:morning_deliveries:tavern", "obj:morning_deliveries:tessa", "obj:morning_deliveries:cliffs"], "maren_return"),
    rule(["quest:morning_deliveries:active"], "maren_waiting", True),
    rule(["quest:morning_deliveries:complete", "!deed_received"], "maren_deed"),
    rule([], "maren_after", True)])
npc("NPC_Bram", "tavern", (-60, 110, 0), 225, "Talk", [rule(["item:parcel_tavern"], "tavern_deliver"), rule([], "tavern_after", True)])
npc("NPC_Tessa", "tessa", (476, 36, 25.6), 200, "Talk to Tessa", [rule(["item:parcel_tessa"], "tessa_deliver"), rule([], "tessa_after", True)])
npc("NPC_Elara", "villager", (535, -98, 1), 0, "Talk", [rule(["item:parcel_cliffs"], "villager_deliver"), rule([], "villager_after", True)])
npc("NPC_Rowan", "rowan", (-8, 14, 0), 180, "Talk to Rowan", [
    rule(["deed_received", "!rowan_inheritance_done"], "rowan_inheritance", set_flag="rowan_inheritance_done"),
    rule(["quest:morning_deliveries:active", "!rowan_morning_done", "!deed_received"], "rowan_morning", set_flag="rowan_morning_done"),
    rule([], "rowan_repeat", True)])
inspect("Inspect_BulletinBoard", (10, -18, 1.5), (0.3, 3, 2.5), "Read", [rule([], "board", True)])
inspect("Inspect_Fountain", (0, 0, 2.2), (7.5, 7.5, 0.1), "Look", [rule([], "fountain", True)])
inspect("Inspect_Windmill", (296, -276, 2), (1, 1, 1), "Look", [rule([], "windmill", True)])
inspect("Inspect_WorkshopDoor", (75, 594.8, 21.5), (2, 0.3, 3), "Enter workshop", [rule(["!deed_received"], "workshop_locked_ch1", True), rule(["!has_glider"], "", event="enter_workshop")])
for jid, c in (("note_cloud_edge", (550, -112, 1.5)), ("note_wind", (300, -262, 3.6)), ("note_sky_map", (512, 40, 25.5)),
               ("note_three_decades", (350, 380, 17.1)), ("note_each_island", (60, 920, -1.5))):
    note(jid, c)
trigger("Trigger_Opening", (320, 320, 17), (8, 8, 4), "opening_seen", "opening")
trigger("Trigger_EdgeWarning", (558, -100, 2), (6, 20, 4), "seen_edge_warning", "edge_warning")
trigger("Trigger_SkywatchHint", (390, 10, 2), (8, 8, 4), "seen_skywatch_hint", "skywatch_hint", ["item:parcel_tessa"])
trigger("Trigger_BluffEdgeWarning", (60, 676, 21.5), (20, 3, 3), "seen_bluff_edge_warning", "edge_warning", ["!piko_joined"])
trigger("Trigger_LaunchReady", (60, 676, 21.5), (20, 3, 3), "seen_launch_ready", "launch_ready", ["piko_joined"])
trigger("Trigger_Fog", (60, 1545, 10), (200, 8, 200), "reached_fog", "wind_refuses", ["piko_joined"])
for a in (("windrest", (0, 40, 10), (230, 260, 40)), ("post_house", (55, 70, 5), (14, 12, 10)), ("tavern", (-70, 120, 5), (16, 14, 10)),
          ("whispermill", (330, -330, 10), (110, 130, 30)), ("skywatch", (480, 40, 30), (25, 25, 12)), ("upper_cliffs", (300, 330, 20), (60, 70, 15)),
          ("bluff", (60, 600, 25), (70, 80, 20)), ("workshop", (80, 600, 24), (9, 7, 6)), ("cloud_edge", (545, -100, 5), (25, 35, 10)),
          ("central_square", (0, 0, 5), (24, 24, 8)), ("orchard_vale", (0, -470, 8), (75, 130, 15)), ("open_sky", (60, 1100, 0), (200, 200, 100))):
    location(*a)
out = {"Note": "Brindle Isle story placements for Unity (metres, Unity axes: x east, y up, z north). Ported from Unreal/Tools/build_brindle_greybox.py; this file is now the source.",
       "Interactables": I, "Triggers": T, "Areas": A}
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else __import__("os").path.join(__import__("os").path.dirname(__file__), "..", "..", "LastSkyfarer", "Assets", "Resources", "Story", "Interactions.json"), "w", encoding="utf-8", newline="\n"), indent=2)
print(len(I), len(T), len(A))

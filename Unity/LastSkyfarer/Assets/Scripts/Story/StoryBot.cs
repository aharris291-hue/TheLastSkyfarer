// The Last Skyfarer: the automated story bot. Plays the whole Milestone A story (Brindle Isle, chapters 1 to 3) through
// the real story rules: it walks into the level's triggers and areas, talks to villagers, inspects and picks things up
// in the order a player would, reads every line, lets the director's fades and queued scenes run, and checks the story
// state after each beat. It also tries things out of order (talking to people early, doors that should stay shut).
// Run from the tests, or in batchmode: -executeMethod LastSkyfarer.EditorTools.StoryBotRunner.Run
using System;
using System.Collections.Generic;
using System.Linq;
using LastSkyfarer.Core;

namespace LastSkyfarer.Story
{
    public class StoryBot
    {
        public struct Result { public string Name; public bool Pass; public string Detail; }

        public readonly StoryManager Story;
        public readonly BrindleStoryDirector Director;
        public readonly List<Result> Results = new List<Result>();
        public readonly HashSet<string> ConversationsPlayed = new HashSet<string>();
        public readonly List<string> Log = new List<string>();
        public int LinesRead { get; private set; }
        public string LastTeleport { get; private set; } = "";
        public float SimulatedSeconds { get; private set; }
        public bool SaveRoundTrip = true;

        public int Passed => Results.Count(r => r.Pass);
        public bool AllPassed => Results.Count > 0 && Results.All(r => r.Pass);

        public StoryBot(NarrativeDatabase db = null)
        {
            Story = new StoryManager(db ?? NarrativeDatabase.LoadFromResources()) { AutosaveEnabled = false };
            Director = new BrindleStoryDirector(Story);
            Story.OnDialogueLine += (conv, line) => { LinesRead++; ConversationsPlayed.Add(conv); };
            Story.OnDialogueEnded += conv => ConversationsPlayed.Add(conv);
            Director.OnTeleport += where => LastTeleport = where;
        }

        void Check(string name, bool pass, string detail = "")
        {
            Results.Add(new Result { Name = name, Pass = pass, Detail = detail });
            Log.Add($"LS_STORYBOT {name} {(pass ? "PASS" : "FAIL")} ({detail})");
        }

        /// <summary>Reads every line and lets the director's queued scenes play until nothing more happens.</summary>
        void Settle()
        {
            for (int guard = 0; guard < 5000; guard++)
            {
                if (Story.IsInDialogue) { Story.AdvanceDialogue(); continue; }
                if (Director.PendingSteps == 0) return;
                Director.Tick(0.1f);
                SimulatedSeconds += 0.1f;
            }
            Check("Settles", false, "the story kept running for 5000 steps");
        }

        InteractableDef It(string id)
        {
            var it = Story.Database.FindInteractable(id);
            if (it == null) Check("Find " + id, false, "not in Interactions.json");
            return it;
        }

        /// <summary>Talk / inspect / pick up, then play whatever follows. Returns the conversation it started ("" if none).</summary>
        string Use(string id)
        {
            var it = It(id);
            if (it == null || !Story.Interact(it)) return null;
            string conv = Story.ActiveConversation;
            Settle();
            return conv;
        }

        void Expect(string step, string id, string conversation)
        {
            string got = Use(id);
            Check(step, got == conversation, $"{id} -> {(got == null ? "nothing to do" : got == "" ? "(no conversation)" : got)}, expected {(conversation == "" ? "(no conversation)" : conversation)}");
        }

        void Enter(string triggerId)
        {
            var t = Story.Database.FindTrigger(triggerId);
            if (t == null) { Check("Find " + triggerId, false, "not in Interactions.json"); return; }
            Story.TryFire(t);
            Settle();
        }

        void Area(string location) => Story.DiscoverLocation(location);

        public void Run()
        {
            Results.Clear();
            var problems = Story.Database.Validate();
            Check("DataValidates", problems.Count == 0, problems.Count == 0 ? "no problems" : string.Join("; ", problems.Take(5)));

            // ---------------- Chapter 1: Morning Deliveries ----------------
            Area("upper_cliffs");
            Enter("Trigger_Opening");
            Check("OpeningStartsQuests", Story.GetQuestState("morning_deliveries") == "Active" && Story.GetQuestState("elias_was_here") == "Active" && Story.HasFlag("opening_done"),
                $"tracked {Story.TrackedQuest}");
            Check("TrackedIsMain", Story.TrackedQuest == "morning_deliveries", Story.TrackedQuest);
            Enter("Trigger_Opening");
            Check("OpeningOnce", ConversationsPlayed.Contains("opening") && Story.HasFlag("opening_seen"), "fires once");
            Expect("NoteThreeDecades", "Note_note_three_decades", "");
            Check("NoteSecondPickupRefused", Use("Note_note_three_decades") == null, "already collected");

            Area("windrest"); Area("central_square");
            Expect("WorkshopLockedInCh1", "Inspect_WorkshopDoor", "workshop_locked_ch1");
            Expect("RowanBeforeMaren", "NPC_Rowan", "rowan_morning");
            Expect("RowanRepeats", "NPC_Rowan", "rowan_repeat");
            Expect("BramBeforeParcels", "NPC_Bram", "tavern_after");
            Expect("Board", "Inspect_BulletinBoard", "board");
            Expect("Fountain", "Inspect_Fountain", "fountain");

            Area("post_house");
            Expect("MarenIntro", "NPC_Maren", "maren_intro");
            Check("ParcelsGiven", Story.GetItemCount("parcel_tavern") == 1 && Story.GetItemCount("parcel_tessa") == 1 && Story.GetItemCount("parcel_cliffs") == 1,
                string.Join(",", Story.Inventory.Keys));
            Check("ReportDone", Story.IsObjectiveDone("morning_deliveries", "report"), "report objective");
            Check("DeliveryObjectivesVisible", Story.GetVisibleObjectives("morning_deliveries").Count == 4, $"{Story.GetVisibleObjectives("morning_deliveries").Count} visible");
            Expect("MarenWaiting", "NPC_Maren", "maren_waiting");

            Area("tavern");
            Expect("TavernDelivery", "NPC_Bram", "tavern_deliver");
            Expect("TavernAfter", "NPC_Bram", "tavern_after");

            Area("whispermill");
            Expect("Windmill", "Inspect_Windmill", "windmill");
            Expect("NoteWind", "Note_note_wind", "");

            Enter("Trigger_SkywatchHint");
            Check("SkywatchHint", ConversationsPlayed.Contains("skywatch_hint"), "hint while carrying Tessa's parcel");
            Area("skywatch");
            Expect("TessaDelivery", "NPC_Tessa", "tessa_deliver");
            Expect("NoteSkyMap", "Note_note_sky_map", "");

            Enter("Trigger_EdgeWarning");
            Area("cloud_edge");
            Expect("CliffsDelivery", "NPC_Elara", "villager_deliver");
            Expect("NoteCloudEdge", "Note_note_cloud_edge", "");
            Expect("ElaraAfter", "NPC_Elara", "villager_after");
            Check("EliasWasHereComplete", Story.GetQuestState("elias_was_here") == "Complete", $"notes {Story.GetObjectiveProgress("elias_was_here", "notes")}/4");
            Check("ParcelsDelivered", !Story.Inventory.Keys.Any(k => k.StartsWith("parcel_")), string.Join(",", Story.Inventory.Keys));
            Check("TessaAfter", Use("NPC_Tessa") == "tessa_after", "Tessa's repeat line");

            // ---------------- Sunset: the deed ----------------
            Expect("MarenReturn", "NPC_Maren", "maren_return");
            Check("MorningDeliveriesComplete", Story.GetQuestState("morning_deliveries") == "Complete" && Story.GetItemCount("courier_wages") == 1, "reward: courier_wages");
            Check("SunsetAndDeed", Story.TimeOfDay == "Sunset" && ConversationsPlayed.Contains("maren_deed") && Story.HasFlag("deed_received"),
                $"{Story.TimeOfDay}, deed {Story.HasFlag("deed_received")}");
            Check("Chapter2", Story.Chapter == 2 && Story.GetQuestState("hidden_workshop") == "Active" && Story.TrackedQuest == "hidden_workshop",
                $"chapter {Story.Chapter}, tracked {Story.TrackedQuest}");
            Check("DeedAutosave", Story.AutosaveCount >= 1, $"{Story.AutosaveCount} autosaves");
            Expect("MarenAfter", "NPC_Maren", "maren_after");
            Expect("RowanInheritance", "NPC_Rowan", "rowan_inheritance");
            Expect("RowanAfterDeed", "NPC_Rowan", "rowan_repeat");

            // ---------------- Chapter 2: The Hidden Workshop ----------------
            Area("bluff");
            Check("GliderNotYet", !Story.CanInteract(It("Inspect_Glider")), "glider hidden before the compass");
            Expect("EnterWorkshop", "Inspect_WorkshopDoor", "");
            Check("InWorkshopAtNight", LastTeleport == BrindleStoryDirector.InteriorSpawn && Story.TimeOfDay == "Night" && Director.MusicCue == "workshop",
                $"{LastTeleport}, {Story.TimeOfDay}, music {Director.MusicCue}");
            Check("WorkshopEntered", Story.IsObjectiveDone("hidden_workshop", "enter") && Story.Discovered.Contains("workshop"), "enter objective");
            Check("FloorboardHidden", !Story.CanInteract(It("Inspect_Floorboard")), "before the search");
            Expect("Portrait", "Inspect_Portrait", "inspect_portrait");
            Expect("Instruments", "Inspect_Instruments", "inspect_instruments");
            Expect("LeaveAtNight", "Inspect_WorkshopDoor_Inside", "workshop_leave_night");
            Expect("Maps", "Inspect_Maps", "inspect_maps");
            Expect("Sketches", "Inspect_Sketches", "inspect_sketches");
            Expect("WeatherLogs", "Inspect_Notes", "inspect_notes");
            Expect("Shelf", "Inspect_Notes", "inspect_shelf");
            Check("SearchDone", Story.IsObjectiveDone("hidden_workshop", "search") && ConversationsPlayed.Contains("search_done"), "Kieran says the search is done");
            Expect("Compartment", "Inspect_Floorboard", "compartment");
            Check("GliderFound", Story.GetItemCount("ancient_glider") == 1 && Story.GetItemCount("flight_goggles") == 1 && Story.GetItemCount("elias_journal") == 1, "glider, goggles, journal");
            Expect("FinalEntry", "Inspect_Floorboard", "final_entry");
            Check("CompassAwakens", ConversationsPlayed.Contains("compass_awakens") && Story.HasFlag("compass_active") && Story.GetItemCount("brass_compass") == 1, "compass");
            Check("HiddenWorkshopComplete", Story.GetQuestState("hidden_workshop") == "Complete", "auto-complete");

            // ---------------- Chapter 3: Into the Clouds ----------------
            Check("NextMorning", Story.Chapter == 3 && Story.TimeOfDay == "Dawn" && Story.HasFlag("chapter3_banner") && LastTeleport == BrindleStoryDirector.DoorSpawn,
                $"chapter {Story.Chapter}, {Story.TimeOfDay}, at {LastTeleport}");
            Check("IntoTheClouds", Story.GetQuestState("into_the_clouds") == "Active" && Story.TrackedQuest == "into_the_clouds", Story.TrackedQuest);
            Check("WorkshopDoorClosedNow", Use("Inspect_WorkshopDoor") == null, "nothing more inside once the glider is his");
            Enter("Trigger_BluffEdgeWarning");
            Check("BluffEdgeWarning", Story.HasFlag("seen_bluff_edge_warning"), "warned before Piko joins");
            Check("GliderAvailable", Story.HasNew(It("Inspect_Glider")), "glider at the Bluff edge");
            Expect("PikoMeeting", "Inspect_Glider", "piko_meeting");
            Check("PikoJoined", Story.HasFlag("piko_joined") && Story.HasFlag("has_glider") && Story.IsObjectiveDone("into_the_clouds", "bluff") && Story.HasJournal("piko_first"), "glider ready");
            Check("GliderGone", !Story.CanInteract(It("Inspect_Glider")), "glider prop taken");
            Enter("Trigger_LaunchReady");
            Check("LaunchReady", ConversationsPlayed.Contains("launch_ready"), "ready to launch");
            Area("open_sky");
            Director.PikoSensedCurrent(1);
            Settle();
            Check("PikoFindsWind", Story.HasFlag(BrindleStoryDirector.RevealedWindFlag) && Story.HasJournal("piko_wind"), "hidden updraft revealed");
            Director.PikoSensedCurrent(2);
            Settle();
            Expect("NoteEachIsland", "Note_note_each_island", "");
            Enter("Trigger_Fog");
            Check("DemoEnd", Story.GetQuestState("into_the_clouds") == "Complete" && Story.HasFlag("demo_complete") && Director.DemoEnded && Director.MusicCue == "fog",
                $"demo ended {Director.DemoEnded}");

            // ---------------- the whole run ----------------
            Check("AllQuestsComplete", Story.Database.Quests.Keys.All(q => Story.GetQuestState(q) == "Complete"),
                string.Join(", ", Story.Database.Quests.Keys.Select(q => $"{q}={Story.GetQuestState(q)}")));
            Check("WholeJournal", Story.Journal.Count == Story.Database.Journal.Count, $"{Story.Journal.Count}/{Story.Database.Journal.Count} entries");
            var unplayed = Story.Database.Conversations.Keys.Where(c => !ConversationsPlayed.Contains(c) && c != "fell").ToList();
            Check("EveryConversationPlayed", unplayed.Count == 0, unplayed.Count == 0 ? $"{ConversationsPlayed.Count} conversations, {LinesRead} lines" : "never played: " + string.Join(", ", unplayed));
            Check("NoStoryProblems", Story.Problems.Count == 0, Story.Problems.Count == 0 ? "none" : string.Join("; ", Story.Problems.Take(5)));
            Check("NoDialogueLeftOpen", !Story.IsInDialogue && Director.PendingSteps == 0, "idle at the end");

            if (SaveRoundTrip)
            {
                // Save the finished story and load it into a fresh manager: everything must come back.
                const string slot = "storybot_check";
                bool saved = Story.SaveToSlot(slot);
                var copy = new StoryManager(Story.Database);
                bool loaded = copy.LoadFromSlot(slot);
                bool same = saved && loaded && copy.Chapter == Story.Chapter && copy.TimeOfDay == Story.TimeOfDay && copy.TrackedQuest == Story.TrackedQuest
                    && copy.Journal.SequenceEqual(Story.Journal) && new HashSet<string>(copy.Flags).SetEquals(Story.Flags)
                    && Story.Database.Quests.Keys.All(q => copy.GetQuestState(q) == Story.GetQuestState(q)) && copy.GetItemCount("brass_compass") == 1;
                Check("SaveRoundTrip", same, $"saved {saved}, loaded {loaded}");
                SaveSystem.Delete(slot);
            }
            Log.Add($"LS_STORYBOT_SUMMARY {Passed}/{Results.Count} passed, {ConversationsPlayed.Count} conversations, {LinesRead} lines, {SimulatedSeconds:F1} s of director time");
        }
    }
}

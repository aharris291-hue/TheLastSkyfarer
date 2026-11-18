// The Last Skyfarer: story systems (data, conditions, actions, quests, journal, dialogue, triggers) and the story bot.
using System.Linq;
using LastSkyfarer.Core;
using LastSkyfarer.Story;
using NUnit.Framework;
using UnityEngine;

namespace LastSkyfarer.Tests
{
    public class StoryTests
    {
        NarrativeDatabase db;
        StoryManager story;

        [SetUp]
        public void Setup()
        {
            db = NarrativeDatabase.LoadFromResources();
            story = new StoryManager(db) { AutosaveEnabled = false };
        }

        [TearDown] public void Clean() => SaveSystem.Delete("story_test_slot");

        [Test]
        public void DataLoadsAndValidates()
        {
            Assert.AreEqual(38, db.Conversations.Count);
            Assert.AreEqual(4, db.Quests.Count);
            Assert.AreEqual(11, db.Journal.Count);
            Assert.AreEqual(9, db.Items.Count);
            Assert.AreEqual(9, db.Speakers.Count);
            Assert.AreEqual(12, db.Locations.Count);
            Assert.AreEqual(22, db.Level.Interactables.Count);
            Assert.AreEqual(6, db.Level.Triggers.Count);
            var problems = db.Validate();
            Assert.IsEmpty(problems, string.Join("\n", problems));
        }

        [Test]
        public void ValidatorCatchesBrokenReferences()
        {
            db.Conversations["opening"].Lines[0].Actions.Add(StoryAction.Of(ActionType.StartQuest, "no_such_quest"));
            db.Conversations["opening"].Lines[0].Actions.Add(new StoryAction { Type = "Teleport", Arg = "x" });
            db.Level.Interactables[0].Rules[0].Conversation = "no_such_conversation";
            db.Level.Triggers[0].Conditions.Add("obj:morning_deliveries:nope");
            var p = db.Validate();
            Assert.IsTrue(p.Any(e => e.Contains("unknown quest no_such_quest")), string.Join("\n", p));
            Assert.IsTrue(p.Any(e => e.Contains("unknown action type Teleport")));
            Assert.IsTrue(p.Any(e => e.Contains("unknown conversation no_such_conversation")));
            Assert.IsTrue(p.Any(e => e.Contains("unknown objective morning_deliveries:nope")));
        }

        [Test]
        public void Conditions()
        {
            Assert.IsTrue(story.Check(""));
            Assert.IsFalse(story.Check("met_maren"));
            Assert.IsTrue(story.Check("!met_maren"));
            story.SetFlag("met_maren");
            Assert.IsTrue(story.Check("met_maren"));
            Assert.IsTrue(story.Check("tod:morning"));
            Assert.IsTrue(story.Check("quest:morning_deliveries:none"));
            story.StartQuest("morning_deliveries");
            Assert.IsTrue(story.Check("quest:morning_deliveries:active"));
            Assert.IsFalse(story.Check("obj:morning_deliveries:report"));
            story.AdvanceObjective("morning_deliveries", "report");
            Assert.IsTrue(story.Check("obj:morning_deliveries:report"));
            Assert.IsFalse(story.Check("item:deed"));
            story.GiveItem("deed");
            Assert.IsTrue(story.CheckAll(new[] { "item:deed", "met_maren", "!nope" }));
        }

        [Test]
        public void QuestsTrackMainFirstAndAutoComplete()
        {
            story.StartQuest("elias_was_here");                 // side quest: tracked because nothing else is
            Assert.AreEqual("elias_was_here", story.TrackedQuest);
            story.StartQuest("hidden_workshop");                // a main quest takes over the tracker
            Assert.AreEqual("hidden_workshop", story.TrackedQuest);
            story.AdvanceObjective("hidden_workshop", "search", 10);
            Assert.AreEqual(3, story.GetObjectiveProgress("hidden_workshop", "search"), "clamped to the count");
            story.AdvanceObjective("hidden_workshop", "enter");
            story.AdvanceObjective("hidden_workshop", "compartment");
            Assert.AreEqual("Active", story.GetQuestState("hidden_workshop"));
            story.AdvanceObjective("hidden_workshop", "journal");
            Assert.AreEqual("Complete", story.GetQuestState("hidden_workshop"));
            Assert.AreEqual("elias_was_here", story.TrackedQuest, "falls back to the side quest");
            story.AdvanceObjective("into_the_clouds", "bluff");   // not started: ignored
            Assert.AreEqual(0, story.GetObjectiveProgress("into_the_clouds", "bluff"));
            Assert.IsEmpty(story.Problems);
        }

        [Test]
        public void CollectiblesAdvanceTheirQuestAndRewardsArrive()
        {
            story.StartQuest("elias_was_here");
            foreach (string n in new[] { "note_wind", "note_sky_map", "note_cloud_edge" }) story.AddJournal(n);
            story.AddJournal("note_wind");                       // twice: counted once
            Assert.AreEqual(3, story.GetObjectiveProgress("elias_was_here", "notes"));
            story.AddJournal("note_each_island");
            Assert.AreEqual("Complete", story.GetQuestState("elias_was_here"));
            story.StartQuest("morning_deliveries");
            story.CompleteQuest("morning_deliveries");
            Assert.AreEqual(1, story.GetItemCount("courier_wages"));
        }

        [Test]
        public void ItemsAndProblems()
        {
            story.GiveItem("parcel_tessa", 2);
            Assert.IsTrue(story.TakeItem("parcel_tessa"));
            Assert.AreEqual(1, story.GetItemCount("parcel_tessa"));
            Assert.IsTrue(story.TakeItem("parcel_tessa"));
            Assert.IsFalse(story.Inventory.ContainsKey("parcel_tessa"));
            UnityEngine.TestTools.LogAssert.ignoreFailingMessages = true;
            Assert.IsFalse(story.TakeItem("parcel_tessa"));
            Assert.AreEqual(1, story.Problems.Count);
        }

        [Test]
        public void DialogueRunsLineActionsAndSkipsEmptyLines()
        {
            int shown = 0; string ended = null;
            story.OnDialogueLine += (c, l) => { shown++; Assert.IsFalse(string.IsNullOrEmpty(l.Text)); };
            story.OnDialogueEnded += c => ended = c;
            Assert.IsTrue(story.StartConversation("opening"));
            Assert.IsTrue(story.IsInDialogue);
            Assert.AreEqual("narrator", story.CurrentLine.Speaker);
            while (story.IsInDialogue) story.AdvanceDialogue();
            Assert.AreEqual("opening", ended);
            Assert.AreEqual(db.Conversations["opening"].Lines.Count(l => l.Text.Length > 0), shown);
            Assert.AreEqual("Active", story.GetQuestState("morning_deliveries"));
            Assert.IsTrue(story.HasFlag("opening_done"));
        }

        [Test]
        public void InteractionRulesPickTheFirstMatchAndRunActionsAfterTheConversation()
        {
            var rowan = db.FindInteractable("NPC_Rowan");
            story.StartQuest("morning_deliveries");
            Assert.IsTrue(story.HasNew(rowan));
            Assert.IsTrue(story.Interact(rowan));
            Assert.AreEqual("rowan_morning", story.ActiveConversation);
            Assert.IsFalse(story.HasFlag("rowan_morning_done"), "set after the conversation, not before");
            Assert.IsFalse(story.Interact(rowan), "no second conversation while one is running");
            while (story.IsInDialogue) story.AdvanceDialogue();
            Assert.IsTrue(story.HasFlag("rowan_morning_done"));
            Assert.IsFalse(story.HasNew(rowan), "only the repeat line is left");
            Assert.IsTrue(story.CanInteract(rowan));
            var floor = db.FindInteractable("Inspect_Floorboard");
            Assert.IsFalse(story.CanInteract(floor), "hidden until the search is done");
        }

        [Test]
        public void TriggersFireOnceAndWaitForDialogue()
        {
            var opening = db.FindTrigger("Trigger_Opening");
            var hint = db.FindTrigger("Trigger_SkywatchHint");
            Assert.IsFalse(story.TryFire(hint), "needs Tessa's parcel");
            Assert.IsTrue(story.TryFire(opening));
            story.GiveItem("parcel_tessa");
            Assert.IsFalse(story.TryFire(hint), "waits while the opening is playing");
            while (story.IsInDialogue) story.AdvanceDialogue();
            Assert.IsTrue(story.TryFire(hint));
            while (story.IsInDialogue) story.AdvanceDialogue();
            Assert.IsFalse(story.TryFire(opening));
            Assert.IsFalse(story.TryFire(hint));
        }

        [Test]
        public void MapKnowledgeAndPins()
        {
            Assert.AreEqual(MapKnowledge.Unknown, story.GetMapKnowledge("skywatch"));
            story.SetFlag("heard_skywatch");
            Assert.AreEqual(MapKnowledge.Rumoured, story.GetMapKnowledge("skywatch"));
            story.DiscoverLocation("skywatch");
            Assert.AreEqual(MapKnowledge.Known, story.GetMapKnowledge("skywatch"));
            for (int i = 0; i < 5; i++) story.AddMapPin(new Vector3(i, 0f, 0f));
            Assert.AreEqual(3, story.MapPins.Count);
            Assert.AreEqual(2f, story.MapPins[0].x, "oldest pins dropped");
        }

        [Test]
        public void StorySavesAndLoads()
        {
            story.StartQuest("morning_deliveries");
            story.AdvanceObjective("morning_deliveries", "report");
            story.GiveItem("parcel_tavern");
            story.SetFlag("opening_done");
            story.AddJournal("note_wind");
            story.SetTimeOfDay("Sunset");
            story.SetChapter(2);
            story.PlayerPose = () => (new Vector3(4f, 5f, 6f), 45f);
            Assert.IsTrue(story.SaveToSlot("story_test_slot"));
            var other = new StoryManager(db);
            Assert.IsTrue(other.LoadFromSlot("story_test_slot"));
            Assert.AreEqual("Sunset", other.TimeOfDay);
            Assert.AreEqual(2, other.Chapter);
            Assert.IsTrue(other.IsObjectiveDone("morning_deliveries", "report"));
            Assert.AreEqual(1, other.GetItemCount("parcel_tavern"));
            Assert.IsTrue(other.HasFlag("opening_done"));
            Assert.IsTrue(other.HasJournal("note_wind"));
            Assert.AreEqual(new Vector3(4f, 5f, 6f), SaveSystem.Load("story_test_slot").PlayerPosition);
        }

        [Test]
        public void StoryBotPlaysMilestoneAFromStartToFinish()
        {
            var bot = new StoryBot(db);
            bot.Run();
            foreach (string l in bot.Log) Debug.Log(l);
            var failed = bot.Results.Where(r => !r.Pass).Select(r => $"{r.Name}: {r.Detail}").ToList();
            Assert.IsEmpty(failed, string.Join("\n", failed));
            Assert.GreaterOrEqual(bot.Results.Count, 60);
        }
    }
}

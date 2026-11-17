// The Last Skyfarer: the narrative database (ported from the Unreal FLSNarrativeDatabase). Reads the story JSON in
// Resources/Story: conversations, quests, journal, items, speakers, locations, story events, and the level's
// interaction rules (Interactions.json: who says what, and when). Validate() lists every broken reference.
using System;
using System.Collections.Generic;
using UnityEngine;

namespace LastSkyfarer.Story
{
    public enum ActionType { SetFlag, ClearFlag, GiveItem, TakeItem, StartQuest, AdvanceObjective, CompleteQuest, AddJournal, Event, TimeOfDay, Chapter, Autosave, Sfx }

    [Serializable]
    public class StoryAction
    {
        public string Type = "";
        public string Arg = "";
        public int Amount = 1;
        public bool TryGetType(out ActionType t) => Enum.TryParse(Type, out t);
        public static StoryAction Of(ActionType t, string arg, int amount = 1) => new StoryAction { Type = t.ToString(), Arg = arg, Amount = amount };
    }

    [Serializable]
    public class DialogueLine
    {
        public string Speaker = "";
        public string Emotion = "";
        public string Text = "";
        public bool bCanon;
        public string VoiceKey = "";
        public List<StoryAction> Actions = new List<StoryAction>();
    }

    [Serializable] public class Conversation { public string Id; public string Source; public List<DialogueLine> Lines = new List<DialogueLine>(); }
    [Serializable] public class ObjectiveDef { public string Id; public string Text; public int Count = 1; public bool bOptional; public List<string> HiddenUntil = new List<string>(); }

    [Serializable]
    public class QuestDef
    {
        public string Id, Title, Description, TurnIn;
        public int Chapter;
        public bool bMain, bAutoComplete;
        public List<string> Rewards = new List<string>();
        public List<ObjectiveDef> Objectives = new List<ObjectiveDef>();
    }

    [Serializable] public class JournalDef { public string Id, Title, Kind, Collectible, Text, Source; public bool bCanon; }
    [Serializable] public class ItemDef { public string Id, Name, Category, Description; }
    [Serializable] public class SpeakerDef { public string Id, DisplayName, Portrait, DefaultEmotion, Color; }
    [Serializable] public class LocationDef { public string Id, Name, Subtitle; }
    [Serializable] public class StoryEventDef { public string Id; public List<StoryAction> Actions = new List<StoryAction>(); }
    [Serializable] public class CollectibleDef { public string Group, Objective; }

    // ---- the level's story placements (Interactions.json, in Unity world metres) ----
    [Serializable]
    public class InteractionRule
    {
        public List<string> If = new List<string>();
        public string Conversation = "";
        public List<StoryAction> Do = new List<StoryAction>();
        public bool Repeat;
    }

    [Serializable]
    public class InteractableDef
    {
        public string Id;
        public string Kind = "inspect";          // npc, inspect, note
        public string Speaker = "";
        public string Prompt = "";
        public Vector3 Position;
        public Vector3 Size;                    // inspectables: the shape Kieran looks at (metres)
        public float Yaw;
        public float Radius = 2f;
        public List<string> AvailableIf = new List<string>();
        public List<InteractionRule> Rules = new List<InteractionRule>();
        public string JournalId = "";           // notes: the rule is built from this (collected_<id>)
    }

    [Serializable]
    public class TriggerDef
    {
        public string Id, OnceFlag, Conversation = "";
        public Vector3 Position, Size;
        public List<string> Conditions = new List<string>();
        public List<StoryAction> Actions = new List<StoryAction>();
    }

    [Serializable] public class LocationAreaDef { public string Id; public Vector3 Position, Size; }

    // JSON file wrappers (JsonUtility needs a root object).
    [Serializable] class ConversationsFile { public List<Conversation> Conversations = new List<Conversation>(); }
    [Serializable] class QuestsFile { public List<QuestDef> Quests = new List<QuestDef>(); }
    [Serializable] class JournalFile { public List<JournalDef> Entries = new List<JournalDef>(); }
    [Serializable] class ItemsFile { public List<ItemDef> Items = new List<ItemDef>(); }
    [Serializable] class SpeakersFile { public List<SpeakerDef> Speakers = new List<SpeakerDef>(); }
    [Serializable] class LocationsFile { public List<LocationDef> Locations = new List<LocationDef>(); }
    [Serializable] class EventsFile { public List<StoryEventDef> Events = new List<StoryEventDef>(); public List<CollectibleDef> CollectibleObjectives = new List<CollectibleDef>(); }

    [Serializable]
    public class InteractionsFile
    {
        public List<InteractableDef> Interactables = new List<InteractableDef>();
        public List<TriggerDef> Triggers = new List<TriggerDef>();
        public List<LocationAreaDef> Areas = new List<LocationAreaDef>();
    }

    public class NarrativeDatabase
    {
        public const string ResourceFolder = "Story/";
        public readonly Dictionary<string, Conversation> Conversations = new Dictionary<string, Conversation>();
        public readonly Dictionary<string, QuestDef> Quests = new Dictionary<string, QuestDef>();
        public readonly Dictionary<string, JournalDef> Journal = new Dictionary<string, JournalDef>();
        public readonly Dictionary<string, ItemDef> Items = new Dictionary<string, ItemDef>();
        public readonly Dictionary<string, SpeakerDef> Speakers = new Dictionary<string, SpeakerDef>();
        public readonly Dictionary<string, LocationDef> Locations = new Dictionary<string, LocationDef>();
        public readonly Dictionary<string, StoryEventDef> Events = new Dictionary<string, StoryEventDef>();
        public readonly Dictionary<string, string> CollectibleObjectives = new Dictionary<string, string>();
        public InteractionsFile Level = new InteractionsFile();
        public readonly List<string> LoadErrors = new List<string>();

        static NarrativeDatabase cached;
        /// <summary>The game's database, loaded once from Resources/Story.</summary>
        public static NarrativeDatabase Default => cached ??= LoadFromResources();

        public static NarrativeDatabase LoadFromResources()
        {
            var db = new NarrativeDatabase();
            string Read(string name)
            {
                var t = Resources.Load<TextAsset>(ResourceFolder + name);
                if (!t) { db.LoadErrors.Add($"missing Resources/{ResourceFolder}{name}.json"); return null; }
                return t.text;
            }
            db.LoadFromJson(Read("Conversations"), Read("Quests"), Read("Journal"), Read("Items"), Read("Speakers"), Read("Locations"), Read("StoryEvents"), Read("Interactions"));
            return db;
        }

        public void LoadFromJson(string conversations, string quests, string journal, string items, string speakers, string locations, string events, string interactions)
        {
            T Parse<T>(string json, string what) where T : new()
            {
                if (string.IsNullOrEmpty(json)) return new T();
                try { return JsonUtility.FromJson<T>(json) ?? new T(); }
                catch (Exception e) { LoadErrors.Add($"{what}: {e.Message}"); return new T(); }
            }
            void Fill<TV>(Dictionary<string, TV> into, IEnumerable<TV> from, Func<TV, string> id, string what)
            {
                foreach (var v in from)
                {
                    string k = id(v);
                    if (string.IsNullOrEmpty(k)) { LoadErrors.Add($"{what}: entry without an Id"); continue; }
                    if (into.ContainsKey(k)) LoadErrors.Add($"{what}: duplicate id {k}");
                    into[k] = v;
                }
            }
            Fill(Conversations, Parse<ConversationsFile>(conversations, "Conversations").Conversations, c => c.Id, "Conversations");
            Fill(Quests, Parse<QuestsFile>(quests, "Quests").Quests, q => q.Id, "Quests");
            Fill(Journal, Parse<JournalFile>(journal, "Journal").Entries, j => j.Id, "Journal");
            Fill(Items, Parse<ItemsFile>(items, "Items").Items, i => i.Id, "Items");
            Fill(Speakers, Parse<SpeakersFile>(speakers, "Speakers").Speakers, s => s.Id, "Speakers");
            Fill(Locations, Parse<LocationsFile>(locations, "Locations").Locations, l => l.Id, "Locations");
            var ev = Parse<EventsFile>(events, "StoryEvents");
            Fill(Events, ev.Events, e => e.Id, "StoryEvents");
            foreach (var c in ev.CollectibleObjectives) CollectibleObjectives[c.Group] = c.Objective;
            Level = Parse<InteractionsFile>(interactions, "Interactions");
            foreach (var n in Level.Interactables) if (n.Kind == "note") n.Rules = NoteRules(n.JournalId);
        }

        /// <summary>A journal page: pick it up once, which sets collected_&lt;id&gt; and adds the entry.</summary>
        public static List<InteractionRule> NoteRules(string journalId) => new List<InteractionRule>
        {
            new InteractionRule
            {
                If = new List<string> { "!collected_" + journalId },
                Do = new List<StoryAction> { StoryAction.Of(ActionType.SetFlag, "collected_" + journalId), StoryAction.Of(ActionType.AddJournal, journalId) },
            },
        };

        public ObjectiveDef FindObjective(string quest, string objective)
        {
            if (quest == null || !Quests.TryGetValue(quest, out var q)) return null;
            return q.Objectives.Find(o => o.Id == objective);
        }

        public InteractableDef FindInteractable(string id) => Level.Interactables.Find(i => i.Id == id);
        public TriggerDef FindTrigger(string id) => Level.Triggers.Find(t => t.Id == id);

        /// <summary>Every broken reference in the data. Empty means the story data is consistent.</summary>
        public List<string> Validate()
        {
            var errors = new List<string>(LoadErrors);

            void CheckObjectiveRef(string reference, string where)
            {
                int i = reference?.IndexOf(':') ?? -1;
                if (i < 0 || FindObjective(reference.Substring(0, i), reference.Substring(i + 1)) == null)
                    errors.Add($"{where}: unknown objective {reference}");
            }
            void CheckActions(List<StoryAction> actions, string where)
            {
                foreach (var a in actions)
                {
                    if (!a.TryGetType(out var t)) { errors.Add($"{where}: unknown action type {a.Type}"); continue; }
                    switch (t)
                    {
                        case ActionType.StartQuest:
                        case ActionType.CompleteQuest:
                            if (!Quests.ContainsKey(a.Arg)) errors.Add($"{where}: unknown quest {a.Arg}");
                            break;
                        case ActionType.AdvanceObjective: CheckObjectiveRef(a.Arg, where); break;
                        case ActionType.GiveItem:
                        case ActionType.TakeItem:
                            if (!Items.ContainsKey(a.Arg)) errors.Add($"{where}: unknown item {a.Arg}");
                            break;
                        case ActionType.AddJournal:
                            if (!Journal.ContainsKey(a.Arg)) errors.Add($"{where}: unknown journal entry {a.Arg}");
                            break;
                    }
                }
            }
            // Conditions (Unity addition: the level's rules are data too, so they are checked as well).
            void CheckConditions(List<string> conditions, string where)
            {
                foreach (string raw in conditions)
                {
                    string c = raw.Trim().TrimStart('!');
                    var p = c.Split(':');
                    if (p.Length == 2 && p[0] == "item" && !Items.ContainsKey(p[1])) errors.Add($"{where}: condition on unknown item {p[1]}");
                    else if (p.Length == 3 && p[0] == "quest" && !Quests.ContainsKey(p[1])) errors.Add($"{where}: condition on unknown quest {p[1]}");
                    else if (p.Length == 3 && p[0] == "quest" && p[2] != "none" && p[2] != "active" && p[2] != "complete") errors.Add($"{where}: unknown quest state {p[2]}");
                    else if (p.Length == 3 && p[0] == "obj" && FindObjective(p[1], p[2]) == null) errors.Add($"{where}: condition on unknown objective {p[1]}:{p[2]}");
                    else if (p.Length == 2 && p[0] == "tod" && Array.IndexOf(StoryManager.TimesOfDay, p[1]) < 0) errors.Add($"{where}: unknown time of day {p[1]}");
                }
            }
            void CheckConversation(string id, string where)
            {
                if (!string.IsNullOrEmpty(id) && !Conversations.ContainsKey(id)) errors.Add($"{where}: unknown conversation {id}");
            }

            foreach (var c in Conversations.Values)
                for (int i = 0; i < c.Lines.Count; i++)
                {
                    var l = c.Lines[i];
                    string where = $"{c.Id}[{i}]";
                    if (!string.IsNullOrEmpty(l.Text) && !Speakers.ContainsKey(l.Speaker)) errors.Add($"{where}: unknown speaker {l.Speaker}");
                    CheckActions(l.Actions, where);
                }
            foreach (var q in Quests.Values)
            {
                foreach (string r in q.Rewards) if (!Items.ContainsKey(r)) errors.Add($"quest {q.Id}: unknown reward {r}");
                foreach (var o in q.Objectives)
                {
                    if (o.Count < 1) errors.Add($"quest {q.Id}: objective {o.Id} needs a count of at least 1");
                    CheckConditions(o.HiddenUntil, $"quest {q.Id}:{o.Id}");
                }
            }
            foreach (var e in Events.Values) CheckActions(e.Actions, $"event {e.Id}");
            foreach (var kv in CollectibleObjectives)
            {
                CheckObjectiveRef(kv.Value, $"collectible group {kv.Key}");
                bool hasEntry = false;
                foreach (var j in Journal.Values) hasEntry |= j.Collectible == kv.Key;
                if (!hasEntry) errors.Add($"collectible group {kv.Key} has no journal entries");
            }

            var ids = new HashSet<string>();
            foreach (var n in Level.Interactables)
            {
                string where = $"interactable {n.Id}";
                if (!ids.Add(n.Id)) errors.Add($"{where}: duplicate id");
                if (n.Kind == "npc" && !Speakers.ContainsKey(n.Speaker)) errors.Add($"{where}: unknown speaker {n.Speaker}");
                if (n.Kind == "note" && !Journal.ContainsKey(n.JournalId)) errors.Add($"{where}: unknown journal entry {n.JournalId}");
                if (n.Rules.Count == 0) errors.Add($"{where}: no rules");
                CheckConditions(n.AvailableIf, where);
                foreach (var r in n.Rules)
                {
                    CheckConditions(r.If, where);
                    CheckConversation(r.Conversation, where);
                    CheckActions(r.Do, where);
                    if (string.IsNullOrEmpty(r.Conversation) && r.Do.Count == 0) errors.Add($"{where}: a rule that does nothing");
                }
            }
            foreach (var t in Level.Triggers)
            {
                string where = $"trigger {t.Id}";
                if (!ids.Add(t.Id)) errors.Add($"{where}: duplicate id");
                if (string.IsNullOrEmpty(t.OnceFlag)) errors.Add($"{where}: needs a OnceFlag");
                CheckConditions(t.Conditions, where);
                CheckConversation(t.Conversation, where);
                CheckActions(t.Actions, where);
            }
            foreach (var a in Level.Areas)
                if (!Locations.ContainsKey(a.Id)) errors.Add($"area {a.Id}: unknown location");
            return errors;
        }
    }
}

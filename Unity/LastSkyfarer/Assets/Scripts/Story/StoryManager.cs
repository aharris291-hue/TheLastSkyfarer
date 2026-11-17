// The Last Skyfarer: story state and rules (ported from the Unreal ULSStorySubsystem with the same behaviour).
// Flags, items, quests and objectives, the journal, discovered places, map pins, time of day, chapter, story events,
// the linear dialogue runner, the level's interaction rules and saving. Plain C#: the game, tests and the story bot
// all drive the same object. Problems collects anything the data asked for that could not be done.
using System;
using System.Collections.Generic;
using LastSkyfarer.Core;
using UnityEngine;

namespace LastSkyfarer.Story
{
    public enum MapKnowledge { Unknown, Rumoured, Known }

    public class StoryManager
    {
        public static readonly string[] TimesOfDay = { "Dawn", "Morning", "Noon", "Sunset", "Night" };
        public const int MaxMapPins = 3;
        public const string AutosaveSlot = "autosave";

        static StoryManager instance;
        /// <summary>The game's story, created on first use with the default database.</summary>
        public static StoryManager Instance => instance ??= new StoryManager(NarrativeDatabase.Default);
        public static void SetInstance(StoryManager story) => instance = story;

        public NarrativeDatabase Database { get; private set; }
        public readonly List<string> Problems = new List<string>();

        // ---- state ----
        readonly HashSet<string> flags = new HashSet<string>();
        readonly Dictionary<string, int> inventory = new Dictionary<string, int>();
        readonly List<QuestProgress> quests = new List<QuestProgress>();     // in start order (tracking picks the oldest)
        readonly List<string> journal = new List<string>();
        readonly List<string> discovered = new List<string>();
        readonly List<Vector3> mapPins = new List<Vector3>();
        public string TrackedQuest { get; private set; } = "";
        public string TimeOfDay { get; private set; } = "Morning";
        public int Chapter { get; private set; } = 1;
        public float PlaytimeSeconds;

        // ---- dialogue ----
        public string ActiveConversation { get; private set; } = "";
        int lineIndex = -1;
        List<StoryAction> pendingActions;      // an interaction's actions, run when its conversation ends
        public bool IsInDialogue => !string.IsNullOrEmpty(ActiveConversation);
        public DialogueLine CurrentLine => IsInDialogue ? Database.Conversations[ActiveConversation].Lines[lineIndex] : null;

        // ---- hooks ----
        public event Action<string, bool> OnFlagChanged;
        public event Action<string, string> OnQuestChanged;      // quest, state
        public event Action<string> OnJournalAdded, OnStoryEvent, OnTimeOfDayChanged, OnSfx, OnDialogueEnded, OnNotify;
        public event Action<int> OnChapterChanged;
        public event Action<string, DialogueLine> OnDialogueLine;
        /// <summary>Where Kieran is, for saves (position, yaw). Set by the level.</summary>
        public Func<(Vector3, float)> PlayerPose;
        public string SceneName = "";
        /// <summary>Tests and the story bot can turn the autosave action off (it then only counts).</summary>
        public bool AutosaveEnabled = true;
        public int AutosaveCount { get; private set; }

        public StoryManager(NarrativeDatabase database)
        {
            Database = database;
            NewGame();
        }

        public void NewGame()
        {
            flags.Clear(); inventory.Clear(); quests.Clear(); journal.Clear(); discovered.Clear(); mapPins.Clear();
            TrackedQuest = ""; TimeOfDay = "Morning"; Chapter = 1; PlaytimeSeconds = 0f;
            ActiveConversation = ""; lineIndex = -1; pendingActions = null;
        }

        void Report(string problem)
        {
            Problems.Add(problem);
            Debug.LogWarning("LS_STORY problem: " + problem);
        }

        // ================================================================ conditions
        public bool Check(string condition)
        {
            string c = (condition ?? "").Trim();
            if (c.Length == 0) return true;
            if (c[0] == '!') return !Check(c.Substring(1));
            var p = c.Split(':');
            if (p.Length == 2 && p[0] == "item") return GetItemCount(p[1]) > 0;
            if (p.Length == 2 && p[0] == "tod") return string.Equals(TimeOfDay, p[1], StringComparison.OrdinalIgnoreCase);
            if (p.Length == 3 && p[0] == "quest") return string.Equals(p[2], QuestStateName(GetQuestState(p[1])), StringComparison.OrdinalIgnoreCase);
            if (p.Length == 3 && p[0] == "obj") return IsObjectiveDone(p[1], p[2]);
            return HasFlag(c);
        }

        public bool CheckAll(IEnumerable<string> conditions)
        {
            if (conditions != null) foreach (string c in conditions) if (!Check(c)) return false;
            return true;
        }

        static string QuestStateName(string state) => state == "Active" ? "active" : state == "Complete" ? "complete" : "none";

        // ================================================================ actions
        public void RunActions(IEnumerable<StoryAction> actions)
        {
            if (actions == null) return;
            foreach (var a in actions) RunAction(a);
        }

        public void RunAction(StoryAction a)
        {
            if (!a.TryGetType(out var type)) { Report($"Unknown action type {a.Type}"); return; }
            switch (type)
            {
                case ActionType.SetFlag: SetFlag(a.Arg, true); break;
                case ActionType.ClearFlag: SetFlag(a.Arg, false); break;
                case ActionType.GiveItem: GiveItem(a.Arg, a.Amount); break;
                case ActionType.TakeItem: TakeItem(a.Arg, a.Amount); break;
                case ActionType.StartQuest: StartQuest(a.Arg); break;
                case ActionType.AdvanceObjective:
                    int i = a.Arg.IndexOf(':');
                    if (i > 0) AdvanceObjective(a.Arg.Substring(0, i), a.Arg.Substring(i + 1), a.Amount);
                    else Report($"Bad objective reference {a.Arg}");
                    break;
                case ActionType.CompleteQuest: CompleteQuest(a.Arg); break;
                case ActionType.AddJournal: AddJournal(a.Arg); break;
                case ActionType.Event: FireEvent(a.Arg); break;
                case ActionType.TimeOfDay: SetTimeOfDay(a.Arg); break;
                case ActionType.Chapter: SetChapter(a.Amount); break;
                case ActionType.Autosave: Autosave(); break;
                case ActionType.Sfx: OnSfx?.Invoke(a.Arg); break;
            }
        }

        // ================================================================ flags and items
        public bool HasFlag(string flag) => flags.Contains(flag);
        public IEnumerable<string> Flags => flags;

        public void SetFlag(string flag, bool set = true)
        {
            if (string.IsNullOrEmpty(flag) || flags.Contains(flag) == set) return;
            if (set) flags.Add(flag); else flags.Remove(flag);
            OnFlagChanged?.Invoke(flag, set);
        }

        public int GetItemCount(string item) => inventory.TryGetValue(item, out int n) ? n : 0;
        public IReadOnlyDictionary<string, int> Inventory => inventory;

        public void GiveItem(string item, int amount = 1)
        {
            inventory[item] = GetItemCount(item) + Mathf.Max(amount, 1);
            if (Database.Items.TryGetValue(item, out var def)) OnNotify?.Invoke("Received: " + def.Name);
        }

        public bool TakeItem(string item, int amount = 1)
        {
            int n = GetItemCount(item);
            if (n < amount) { Report($"TakeItem {item} x{amount} without having it"); return false; }
            if (n - amount <= 0) inventory.Remove(item); else inventory[item] = n - amount;
            return true;
        }

        // ================================================================ quests
        QuestProgress Progress(string quest) => quests.Find(q => q.Quest == quest);
        public IReadOnlyList<QuestProgress> Quests => quests;

        /// <summary>"None", "Active" or "Complete".</summary>
        public string GetQuestState(string quest) => Progress(quest)?.State ?? "None";

        public int GetObjectiveProgress(string quest, string objective)
        {
            var e = Progress(quest)?.Objectives.Find(o => o.Key == objective);
            return e?.Value ?? 0;
        }

        public bool IsObjectiveDone(string quest, string objective)
        {
            if (GetQuestState(quest) == "Complete") return true;
            var def = Database.FindObjective(quest, objective);
            return def != null && GetObjectiveProgress(quest, objective) >= def.Count;
        }

        public List<ObjectiveDef> GetVisibleObjectives(string quest)
        {
            var list = new List<ObjectiveDef>();
            if (Database.Quests.TryGetValue(quest, out var q))
                foreach (var o in q.Objectives) if (CheckAll(o.HiddenUntil)) list.Add(o);
            return list;
        }

        public void SetTrackedQuest(string quest) => TrackedQuest = quest ?? "";

        public void StartQuest(string quest)
        {
            if (!Database.Quests.TryGetValue(quest, out var def)) { Report($"StartQuest: unknown quest {quest}"); return; }
            if (GetQuestState(quest) != "None") return;
            quests.Add(new QuestProgress { Quest = quest, State = "Active" });
            if (def.bMain || string.IsNullOrEmpty(TrackedQuest)) TrackedQuest = quest;
            OnNotify?.Invoke("New quest: " + def.Title);
            OnQuestChanged?.Invoke(quest, "Active");
        }

        public void AdvanceObjective(string quest, string objective, int amount = 1)
        {
            var def = Database.FindObjective(quest, objective);
            if (def == null) { Report($"AdvanceObjective: unknown objective {quest}:{objective}"); return; }
            if (GetQuestState(quest) != "Active") return;
            var p = Progress(quest);
            var e = p.Objectives.Find(o => o.Key == objective);
            if (e == null) { e = new IntEntry { Key = objective }; p.Objectives.Add(e); }
            int before = e.Value;
            e.Value = Mathf.Min(e.Value + Mathf.Max(amount, 1), def.Count);
            if (e.Value != before)
            {
                if (e.Value >= def.Count) OnNotify?.Invoke("Done: " + def.Text);
                OnQuestChanged?.Invoke(quest, "Active");
            }
            TryAutoComplete(quest);
        }

        void TryAutoComplete(string quest)
        {
            if (!Database.Quests.TryGetValue(quest, out var def) || !def.bAutoComplete || GetQuestState(quest) != "Active") return;
            foreach (var o in def.Objectives) if (!o.bOptional && !IsObjectiveDone(quest, o.Id)) return;
            CompleteQuest(quest);
        }

        public void CompleteQuest(string quest)
        {
            if (!Database.Quests.TryGetValue(quest, out var def) || GetQuestState(quest) != "Active") return;
            Progress(quest).State = "Complete";
            foreach (string r in def.Rewards) GiveItem(r, 1);
            if (TrackedQuest == quest)
            {
                // Track the next active quest, main quests first.
                TrackedQuest = "";
                for (int pass = 0; pass < 2 && TrackedQuest.Length == 0; pass++)
                    foreach (var p in quests)
                        if (p.State == "Active" && Database.Quests.TryGetValue(p.Quest, out var other) && (pass == 1 || other.bMain)) { TrackedQuest = p.Quest; break; }
            }
            OnNotify?.Invoke("Quest complete: " + def.Title);
            OnQuestChanged?.Invoke(quest, "Complete");
        }

        // ================================================================ journal and world
        public bool HasJournal(string entry) => journal.Contains(entry);
        public IReadOnlyList<string> Journal => journal;

        public void AddJournal(string entry)
        {
            if (!Database.Journal.TryGetValue(entry, out var def)) { Report($"AddJournal: unknown entry {entry}"); return; }
            if (journal.Contains(entry)) return;
            journal.Add(entry);
            OnNotify?.Invoke("Journal: " + def.Title);
            OnJournalAdded?.Invoke(entry);
            if (!string.IsNullOrEmpty(def.Collectible) && Database.CollectibleObjectives.TryGetValue(def.Collectible, out string reference))
            {
                int i = reference.IndexOf(':');
                if (i > 0 && GetQuestState(reference.Substring(0, i)) == "Active") AdvanceObjective(reference.Substring(0, i), reference.Substring(i + 1), 1);
            }
        }

        public IReadOnlyList<string> Discovered => discovered;

        public void DiscoverLocation(string location)
        {
            if (string.IsNullOrEmpty(location) || discovered.Contains(location)) return;
            discovered.Add(location);
            if (Database.Locations.TryGetValue(location, out var def)) OnNotify?.Invoke(def.Name);
        }

        public MapKnowledge GetMapKnowledge(string location) =>
            discovered.Contains(location) ? MapKnowledge.Known : HasFlag("heard_" + location) ? MapKnowledge.Rumoured : MapKnowledge.Unknown;

        public IReadOnlyList<Vector3> MapPins => mapPins;
        public void AddMapPin(Vector3 at) { if (mapPins.Count >= MaxMapPins) mapPins.RemoveAt(0); mapPins.Add(at); }
        public void RemoveMapPin(int index) { if (index >= 0 && index < mapPins.Count) mapPins.RemoveAt(index); }

        public void SetTimeOfDay(string tod)
        {
            if (Array.IndexOf(TimesOfDay, tod) < 0) { Report($"Unknown time of day {tod}"); return; }
            if (TimeOfDay == tod) return;
            TimeOfDay = tod;
            OnTimeOfDayChanged?.Invoke(tod);
        }

        public void SetChapter(int chapter)
        {
            if (Chapter == chapter) return;
            Chapter = chapter;
            OnChapterChanged?.Invoke(chapter);
        }

        public void FireEvent(string id)
        {
            if (Database.Events.TryGetValue(id, out var def)) RunActions(def.Actions);
            OnStoryEvent?.Invoke(id);
        }

        public void Notify(string message) => OnNotify?.Invoke(message);

        // ================================================================ dialogue
        public bool StartConversation(string id)
        {
            if (IsInDialogue) { Report($"StartConversation {id} while {ActiveConversation} is running"); return false; }
            if (!Database.Conversations.ContainsKey(id)) { Report($"StartConversation: unknown conversation {id}"); return false; }
            ActiveConversation = id;
            lineIndex = -1;
            ShowNextLine();
            return true;
        }

        /// <summary>The player pressed Interact/Jump while a line is showing.</summary>
        public void AdvanceDialogue() { if (IsInDialogue) ShowNextLine(); }

        void ShowNextLine()
        {
            var conv = Database.Conversations[ActiveConversation];
            while (++lineIndex < conv.Lines.Count)
            {
                var line = conv.Lines[lineIndex];
                RunActions(line.Actions);
                if (!string.IsNullOrEmpty(line.Text)) { OnDialogueLine?.Invoke(ActiveConversation, line); return; }
            }
            string ended = ActiveConversation;
            ActiveConversation = "";
            lineIndex = -1;
            var after = pendingActions;
            pendingActions = null;
            OnDialogueEnded?.Invoke(ended);
            RunActions(after);
        }

        /// <summary>Runs every action in a conversation without showing it (skips, tests).</summary>
        public void RunConversationInstant(string id)
        {
            if (Database.Conversations.TryGetValue(id, out var conv)) foreach (var l in conv.Lines) RunActions(l.Actions);
            else Report($"RunConversationInstant: unknown conversation {id}");
        }

        // ================================================================ the level's interaction rules
        public static int PickRule(List<InteractionRule> rules, StoryManager story)
        {
            for (int i = 0; i < rules.Count; i++) if (story.CheckAll(rules[i].If)) return i;
            return -1;
        }

        public bool CanInteract(InteractableDef it) => CheckAll(it.AvailableIf) && PickRule(it.Rules, this) >= 0;

        /// <summary>Something new to hear or do here (the marker over a villager's head).</summary>
        public bool HasNew(InteractableDef it)
        {
            int i = PickRule(it.Rules, this);
            return CheckAll(it.AvailableIf) && i >= 0 && !it.Rules[i].Repeat;
        }

        /// <summary>Talks to / inspects / picks up. The rule's actions run after its conversation (or at once).</summary>
        public bool Interact(InteractableDef it)
        {
            if (IsInDialogue || !CanInteract(it)) return false;
            var rule = it.Rules[PickRule(it.Rules, this)];
            if (!string.IsNullOrEmpty(rule.Conversation))
            {
                if (!StartConversation(rule.Conversation)) return false;
                if (IsInDialogue) pendingActions = rule.Do;
                else RunActions(rule.Do);          // a conversation with no text lines ends at once
            }
            else RunActions(rule.Do);
            return true;
        }

        /// <summary>A story trigger the player walked into. Fires once (OnceFlag); waits if a conversation is running.</summary>
        public bool TryFire(TriggerDef t)
        {
            if (string.IsNullOrEmpty(t.OnceFlag) || HasFlag(t.OnceFlag) || !CheckAll(t.Conditions)) return false;
            if (!string.IsNullOrEmpty(t.Conversation) && IsInDialogue) return false;
            SetFlag(t.OnceFlag);
            RunActions(t.Actions);
            if (!string.IsNullOrEmpty(t.Conversation)) StartConversation(t.Conversation);
            return true;
        }

        // ================================================================ saves
        public StorySaveData ToSaveData()
        {
            var d = new StorySaveData
            {
                Flags = new List<string>(flags),
                TrackedQuest = TrackedQuest,
                Journal = new List<string>(journal),
                Discovered = new List<string>(discovered),
                TimeOfDay = TimeOfDay,
                Chapter = Chapter,
                PlaytimeSeconds = PlaytimeSeconds,
                SceneName = SceneName,
                MapPins = new List<Vector3>(mapPins),
            };
            foreach (var kv in inventory) d.Inventory.Add(new IntEntry { Key = kv.Key, Value = kv.Value });
            foreach (var q in quests)
            {
                var copy = new QuestProgress { Quest = q.Quest, State = q.State };
                foreach (var o in q.Objectives) copy.Objectives.Add(new IntEntry { Key = o.Key, Value = o.Value });
                d.Quests.Add(copy);
            }
            if (PlayerPose != null) (d.PlayerPosition, d.PlayerYaw) = PlayerPose();
            return d;
        }

        public void FromSaveData(StorySaveData d)
        {
            NewGame();
            foreach (string f in d.Flags) flags.Add(f);
            foreach (var e in d.Inventory) if (e.Value > 0) inventory[e.Key] = e.Value;
            foreach (var q in d.Quests)
            {
                if (!Database.Quests.ContainsKey(q.Quest)) { Report($"Save: unknown quest {q.Quest} ignored"); continue; }
                quests.Add(new QuestProgress { Quest = q.Quest, State = q.State == "Completed" ? "Complete" : q.State, Objectives = new List<IntEntry>(q.Objectives) });
            }
            journal.AddRange(d.Journal);
            discovered.AddRange(d.Discovered);
            mapPins.AddRange(d.MapPins);
            TrackedQuest = d.TrackedQuest ?? "";
            TimeOfDay = Array.IndexOf(TimesOfDay, d.TimeOfDay) >= 0 ? d.TimeOfDay : "Morning";
            Chapter = Mathf.Max(1, d.Chapter);
            PlaytimeSeconds = d.PlaytimeSeconds;
            OnTimeOfDayChanged?.Invoke(TimeOfDay);
            OnChapterChanged?.Invoke(Chapter);
        }

        public bool SaveToSlot(string slot) => SaveSystem.Save(ToSaveData(), slot);

        public bool LoadFromSlot(string slot)
        {
            var d = SaveSystem.Load(slot);
            if (d == null) return false;
            FromSaveData(d);
            return true;
        }

        public void Autosave()
        {
            AutosaveCount++;
            if (AutosaveEnabled) SaveToSlot(AutosaveSlot);
        }
    }
}

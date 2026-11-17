// The Last Skyfarer: Brindle Isle story director (ported from the Unreal ALSBrindleStory). Reacts to story events
// (sunset, the workshop, the compass, the next morning, Piko, the fog) by queueing conversations and timed steps.
// Plain C#: the level ticks it and listens to its hooks (fades, teleports, music, world state); tests tick it directly.
// Queued steps wait while a conversation is running, exactly as in the Unreal build.
using System;
using System.Collections.Generic;

namespace LastSkyfarer.Story
{
    public class BrindleStoryDirector : IDisposable
    {
        public const string RevealedWindFlag = "revealed_wind_1";
        public const string InteriorSpawn = "workshop_interior", DoorSpawn = "workshop_door";

        struct Step { public float Delay; public string Conversation; public Action Run; }

        readonly StoryManager story;
        readonly List<Step> steps = new List<Step>();
        public bool InWorkshop { get; private set; }
        public bool DemoEnded { get; private set; }
        public string MusicCue { get; private set; } = "";
        public int PendingSteps => steps.Count;

        // ---- hooks for the level ----
        public event Action<float> OnFadeOut, OnFadeIn;          // seconds
        public event Action<string> OnTeleport;                   // InteriorSpawn or DoorSpawn
        public event Action<string> OnMusicCue;
        public event Action OnApplyStoryState;                    // glider prop, Piko, edge wall, compartment, wind
        public event Action OnDemoEnd;

        public BrindleStoryDirector(StoryManager story)
        {
            this.story = story;
            story.OnStoryEvent += HandleStoryEvent;
            story.OnFlagChanged += HandleFlagChanged;
            story.OnTimeOfDayChanged += HandleTimeOfDay;
            HandleTimeOfDay(story.TimeOfDay);
        }

        public void Dispose()
        {
            story.OnStoryEvent -= HandleStoryEvent;
            story.OnFlagChanged -= HandleFlagChanged;
            story.OnTimeOfDayChanged -= HandleTimeOfDay;
        }

        void Queue(string conversation, float delay = 0f) => steps.Add(new Step { Delay = delay, Conversation = conversation });
        void QueueRun(Action run, float delay = 0f) => steps.Add(new Step { Delay = delay, Run = run });

        /// <summary>Fade to black, do the change once fully black, optionally a second change, then fade back in.</summary>
        void FadeThrough(Action middle, string caption = null, Action thenWhileBlack = null)
        {
            QueueRun(() => { OnFadeOut?.Invoke(0.6f); if (!string.IsNullOrEmpty(caption)) story.Notify(caption); });
            QueueRun(middle, 0.8f);
            if (thenWhileBlack != null) QueueRun(thenWhileBlack, 0.4f);
            QueueRun(() => OnFadeIn?.Invoke(1f), 0.6f);
        }

        void Teleport(string where)
        {
            InWorkshop = where == InteriorSpawn;
            OnTeleport?.Invoke(where);
            if (InWorkshop) PlayMusic("workshop");
        }

        void PlayMusic(string cue)
        {
            if (cue == MusicCue) return;
            MusicCue = cue;
            OnMusicCue?.Invoke(cue);
        }

        void HandleTimeOfDay(string tod)
        {
            if (InWorkshop) return;     // the workshop keeps Elias's piece while Kieran is inside
            PlayMusic(tod == "Sunset" ? "village_sunset" : tod == "Night" ? "village_night" : tod == "Dawn" ? "dawn" : "village_day");
        }

        void HandleStoryEvent(string id)
        {
            switch (id)
            {
                case "sunset_fade":
                    FadeThrough(() => story.SetTimeOfDay("Sunset"), "Later that day...");
                    Queue("maren_deed", 0.6f);
                    break;
                case "enter_workshop":
                    InWorkshop = true;
                    PlayMusic("workshop");
                    // Indoors at night: lamplight inside, moonlight outside.
                    FadeThrough(() => Teleport(InteriorSpawn), null, () => story.SetTimeOfDay("Night"));
                    if (!story.HasFlag("workshop_entered"))
                    {
                        QueueRun(() =>
                        {
                            story.SetFlag("workshop_entered");
                            story.DiscoverLocation("workshop");
                            story.Notify("Chapter 2: The Hidden Workshop");
                        });
                        Queue("workshop_enter", 1.2f);
                    }
                    break;
                case "compass_awakens":
                    Queue("compass_awakens", 0.4f);
                    break;
                case "next_morning":
                    // StoryEvents.json has already moved the story to Chapter 3 at dawn and started Into the Clouds.
                    // Keep the night lighting until the screen is black outside the door, then let dawn come in.
                    InWorkshop = false;
                    PlayMusic("dawn");
                    story.SetTimeOfDay("Night");
                    QueueRun(() => story.Notify("Chapter 2 complete. An impossible wind current appears on the map."));
                    FadeThrough(() => { Teleport(DoorSpawn); OnApplyStoryState?.Invoke(); story.SetFlag("chapter3_banner"); }, null, () => story.SetTimeOfDay("Dawn"));
                    QueueRun(() => { story.Notify("Chapter 3: Into the Clouds"); story.Autosave(); }, 0.5f);
                    break;
                case "leave":
                    FadeThrough(() => { Teleport(DoorSpawn); HandleTimeOfDay(story.TimeOfDay); });
                    break;
                case "piko_joins":
                    story.SetFlag("has_glider");
                    OnApplyStoryState?.Invoke();
                    QueueRun(() =>
                    {
                        story.Notify("Jump off the edge, then press Jump again to glide. Rising wind lifts you higher.");
                        story.Autosave();
                    });
                    break;
                case "demo_end":
                    PlayMusic("fog");
                    QueueRun(() =>
                    {
                        story.Autosave();
                        DemoEnded = true;
                        OnDemoEnd?.Invoke();
                        story.Notify("End of the Windrest demo. Thank you for playing.");
                    }, 0.6f);
                    break;
            }
        }

        void HandleFlagChanged(string flag, bool set)
        {
            if (!set) return;
            if (flag == "compartment_open" || flag == "compass_active" || flag == "piko_joined") OnApplyStoryState?.Invoke();
            // Once the three searches are done, Kieran says so (once).
            if ((flag == "searched_maps" || flag == "searched_sketches" || flag == "searched_notes")
                && story.IsObjectiveDone("hidden_workshop", "search") && !story.HasFlag("search_done_said"))
            {
                story.SetFlag("search_done_said");
                Queue("search_done", 0.3f);
            }
        }

        /// <summary>Piko found hidden wind near Kieran.</summary>
        public void PikoSensedCurrent(int numRevealed)
        {
            if (numRevealed <= 0) return;
            story.SetFlag(RevealedWindFlag);
            if (!story.HasFlag("seen_piko_wind"))
            {
                story.SetFlag("seen_piko_wind");
                Queue("piko_found_wind", 0.4f);
            }
        }

        public void Tick(float dt)
        {
            if (steps.Count == 0 || story.IsInDialogue) return;
            var s = steps[0];
            s.Delay -= dt;
            if (s.Delay > 0f) { steps[0] = s; return; }
            steps.RemoveAt(0);
            if (!string.IsNullOrEmpty(s.Conversation)) story.StartConversation(s.Conversation);
            s.Run?.Invoke();
        }
    }
}

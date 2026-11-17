// The Last Skyfarer: a plain stand-in HUD until the real UI (U6): the interact prompt, the dialogue box, quest toasts,
// the tracked objective and the story's fades. Drawn with IMGUI, so it needs no assets.
using System.Collections.Generic;
using LastSkyfarer.Story;
using UnityEngine;

namespace LastSkyfarer.World
{
    public class DevStoryHud : MonoBehaviour
    {
        public BrindleLevel Level;
        public bool ShowHud = true;
        float fade, fadeTarget, fadeSpeed = 1f;
        readonly Queue<string> toasts = new Queue<string>();
        string toast = ""; float toastTime;
        GUIStyle box, title, body, small;

        public float FadeAlpha => fade;
        public void FadeTo(float alpha, float seconds) { fadeTarget = alpha; fadeSpeed = seconds > 0f ? 1f / seconds : 1000f; }

        void OnEnable() => StoryManager.Instance.OnNotify += Notify;
        void OnDisable() => StoryManager.Instance.OnNotify -= Notify;
        void Notify(string m) { if (toasts.Count < 6) toasts.Enqueue(m); }

        void Update()
        {
            fade = Mathf.MoveTowards(fade, fadeTarget, fadeSpeed * Time.deltaTime);
            toastTime -= Time.deltaTime;
            if (toastTime <= 0f) { toast = toasts.Count > 0 ? toasts.Dequeue() : ""; toastTime = toast.Length > 0 ? 2.6f : 0f; }
        }

        void Styles()
        {
            if (box != null) return;
            var bg = new Texture2D(1, 1); bg.SetPixel(0, 0, new Color(0.08f, 0.07f, 0.1f, 0.78f)); bg.Apply();
            box = new GUIStyle { normal = { background = bg }, padding = new RectOffset(18, 18, 12, 12) };
            title = new GUIStyle { fontSize = 22, fontStyle = FontStyle.Bold, normal = { textColor = Color.white } };
            body = new GUIStyle { fontSize = 20, wordWrap = true, normal = { textColor = new Color(0.97f, 0.95f, 0.9f) } };
            small = new GUIStyle { fontSize = 17, wordWrap = true, normal = { textColor = new Color(0.95f, 0.93f, 0.88f) } };
        }

        void OnGUI()
        {
            Styles();
            var story = StoryManager.Instance;
            float w = Screen.width, h = Screen.height, s = h / 1080f;
            var old = GUI.matrix;
            GUI.matrix = Matrix4x4.Scale(new Vector3(s, s, 1f));
            float vw = w / s;
            if (ShowHud)
            {
                if (story.IsInDialogue && story.CurrentLine != null)
                {
                    var line = story.CurrentLine;
                    var r = new Rect(vw * 0.5f - 560f, 1080f - 250f, 1120f, 200f);
                    GUI.Box(r, GUIContent.none, box);
                    story.Database.Speakers.TryGetValue(line.Speaker, out var sp);
                    title.normal.textColor = sp != null && ColorUtility.TryParseHtmlString(sp.Color, out var c) ? c : Color.white;
                    GUI.Label(new Rect(r.x + 24f, r.y + 16f, r.width - 48f, 30f), sp != null ? sp.DisplayName : line.Speaker, title);
                    GUI.Label(new Rect(r.x + 24f, r.y + 54f, r.width - 48f, 120f), line.Text, body);
                    GUI.Label(new Rect(r.xMax - 210f, r.yMax - 34f, 200f, 24f), "E  continue", small);
                }
                else if (Level && Level.Kieran)
                {
                    var focus = Level.Kieran.GetComponent<KieranInteractor>()?.Focus;
                    if (focus) { var r = new Rect(vw * 0.5f - 160f, 1080f - 190f, 320f, 50f); GUI.Box(r, GUIContent.none, box); GUI.Label(new Rect(r.x + 18f, r.y + 12f, 290f, 30f), "E   " + focus.Def.Prompt, body); }
                }
                if (!string.IsNullOrEmpty(story.TrackedQuest) && story.Database.Quests.TryGetValue(story.TrackedQuest, out var q))
                {
                    var r = new Rect(vw - 470f, 40f, 430f, 40f);
                    var lines = new List<string>();
                    foreach (var o in story.GetVisibleObjectives(q.Id)) if (!story.IsObjectiveDone(q.Id, o.Id)) lines.Add("•  " + o.Text + (o.Count > 1 ? $"  ({story.GetObjectiveProgress(q.Id, o.Id)}/{o.Count})" : ""));
                    r.height = 56f + lines.Count * 28f;
                    GUI.Box(r, GUIContent.none, box);
                    title.normal.textColor = new Color(1f, 0.86f, 0.6f);
                    GUI.Label(new Rect(r.x + 18f, r.y + 12f, r.width - 36f, 28f), q.Title, title);
                    for (int i = 0; i < lines.Count; i++) GUI.Label(new Rect(r.x + 18f, r.y + 46f + i * 28f, r.width - 36f, 28f), lines[i], small);
                }
                if (toast.Length > 0) { var r = new Rect(vw * 0.5f - 300f, 70f, 600f, 52f); GUI.Box(r, GUIContent.none, box); GUI.Label(new Rect(r.x + 20f, r.y + 13f, 560f, 30f), toast, body); }
            }
            GUI.matrix = old;
            if (fade > 0.001f)
            {
                var c = GUI.color; GUI.color = new Color(0f, 0f, 0f, fade);
                GUI.DrawTexture(new Rect(0, 0, w, h), Texture2D.whiteTexture);
                GUI.color = c;
            }
        }
    }
}

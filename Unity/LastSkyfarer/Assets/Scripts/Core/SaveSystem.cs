// The Last Skyfarer: save game (ported from the Unreal FLSStorySaveData). JSON in the player's save folder, written
// atomically (temp file, then swap) so a crash mid-save never corrupts the slot.
using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace LastSkyfarer.Core
{
    [Serializable] public class IntEntry { public string Key; public int Value; }

    [Serializable]
    public class QuestProgress
    {
        public string Quest;
        public string State = "None";                // None, Active, Complete
        public List<IntEntry> Objectives = new List<IntEntry>();
    }

    [Serializable]
    public class StorySaveData
    {
        public const int CurrentVersion = 1;
        public int Version = CurrentVersion;
        public List<string> Flags = new List<string>();
        public List<IntEntry> Inventory = new List<IntEntry>();
        public List<QuestProgress> Quests = new List<QuestProgress>();
        public string TrackedQuest = "";
        public List<string> Journal = new List<string>();
        public List<string> Discovered = new List<string>();
        public string TimeOfDay = "Morning";
        public int Chapter = 1;
        public float PlaytimeSeconds;
        public string SceneName = "";
        public Vector3 PlayerPosition;
        public float PlayerYaw;
        public List<Vector3> MapPins = new List<Vector3>();   // GDD 9: up to 3
        public string SavedAtUtc = "";
    }

    public static class SaveSystem
    {
        public const string DefaultSlot = "milestone_a";
        public static string Folder => Path.Combine(Application.persistentDataPath, "saves");
        public static string PathFor(string slot) => Path.Combine(Folder, slot + ".json");

        public static bool Exists(string slot = DefaultSlot) => File.Exists(PathFor(slot));

        public static bool Save(StorySaveData data, string slot = DefaultSlot)
        {
            try
            {
                Directory.CreateDirectory(Folder);
                data.Version = StorySaveData.CurrentVersion;
                data.SavedAtUtc = DateTime.UtcNow.ToString("o");
                string final = PathFor(slot), temp = final + ".tmp";
                File.WriteAllText(temp, JsonUtility.ToJson(data, true));
                if (File.Exists(final)) File.Replace(temp, final, null);
                else File.Move(temp, final);
                return true;
            }
            catch (Exception e)
            {
                Debug.LogError("LS_SAVE failed: " + e.Message);
                return false;
            }
        }

        public static StorySaveData Load(string slot = DefaultSlot)
        {
            try
            {
                if (!Exists(slot)) return null;
                var data = JsonUtility.FromJson<StorySaveData>(File.ReadAllText(PathFor(slot)));
                if (data == null || data.Version > StorySaveData.CurrentVersion) return null;   // from a newer build: don't guess
                return data;
            }
            catch (Exception e)
            {
                Debug.LogWarning("LS_SAVE load failed (slot ignored): " + e.Message);
                return null;
            }
        }

        public static void Delete(string slot = DefaultSlot)
        {
            if (Exists(slot)) File.Delete(PathFor(slot));
        }
    }
}

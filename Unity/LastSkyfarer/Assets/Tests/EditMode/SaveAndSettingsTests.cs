// The Last Skyfarer: save/Continue and settings.
using LastSkyfarer.Core;
using NUnit.Framework;
using UnityEngine;

namespace LastSkyfarer.Tests
{
    public class SaveAndSettingsTests
    {
        const string Slot = "unit_test_slot";

        [TearDown] public void Clean() => SaveSystem.Delete(Slot);

        [Test]
        public void SaveRoundTripsEverything()
        {
            var d = new StorySaveData { TrackedQuest = "mq_01", TimeOfDay = "Sunset", Chapter = 2, PlaytimeSeconds = 125.5f,
                                        SceneName = "Brindle", PlayerPosition = new Vector3(1f, 2f, 3f), PlayerYaw = 90f };
            d.Flags.Add("met_maren");
            d.Inventory.Add(new IntEntry { Key = "brass_compass", Value = 1 });
            var q = new QuestProgress { Quest = "mq_01", State = "Active" };
            q.Objectives.Add(new IntEntry { Key = "deliver", Value = 2 });
            d.Quests.Add(q);
            d.Journal.Add("entry_01");
            d.Discovered.Add("windrest");
            d.MapPins.Add(new Vector3(5f, 0f, 6f));
            Assert.IsTrue(SaveSystem.Save(d, Slot));
            Assert.IsTrue(SaveSystem.Exists(Slot));
            var l = SaveSystem.Load(Slot);
            Assert.AreEqual("mq_01", l.TrackedQuest);
            Assert.AreEqual("Sunset", l.TimeOfDay);
            Assert.AreEqual(2, l.Chapter);
            Assert.AreEqual(new Vector3(1f, 2f, 3f), l.PlayerPosition);
            Assert.AreEqual("met_maren", l.Flags[0]);
            Assert.AreEqual(1, l.Inventory[0].Value);
            Assert.AreEqual(2, l.Quests[0].Objectives[0].Value);
            Assert.AreEqual(1, l.MapPins.Count);
            Assert.IsNotEmpty(l.SavedAtUtc);
        }

        [Test]
        public void MissingOrNewerSavesAreNotLoaded()
        {
            Assert.IsNull(SaveSystem.Load(Slot));
            SaveSystem.Save(new StorySaveData(), Slot);
            System.IO.File.WriteAllText(SaveSystem.PathFor(Slot), "{\"Version\": 99}");
            Assert.IsNull(SaveSystem.Load(Slot), "a save from a newer build is not guessed at");
            System.IO.File.WriteAllText(SaveSystem.PathFor(Slot), "not json");
            Assert.IsNull(SaveSystem.Load(Slot), "a broken file does not crash");
        }

        [Test]
        public void IntegratedGraphicsAreDetected()
        {
            Assert.IsTrue(GameSettings.IsIntegratedGpu("Intel(R) UHD Graphics 630", 0x8086));
            Assert.IsFalse(GameSettings.IsIntegratedGpu("Intel(R) Arc(TM) A770", 0x8086));
            Assert.IsFalse(GameSettings.IsIntegratedGpu("NVIDIA GeForce RTX 3060", 0x10DE));
        }

        [Test]
        public void LowIsADefinedQualityLevel()
        {
            CollectionAssert.Contains(QualitySettings.names, "Low");
        }
    }
}

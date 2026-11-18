// The Last Skyfarer: runs the story bot in batchmode and writes its report.
//   Unity.exe -batchmode -nographics -projectPath <project> -executeMethod LastSkyfarer.EditorTools.StoryBotRunner.Run -quit
using System.IO;
using LastSkyfarer.Story;
using UnityEditor;
using UnityEngine;

namespace LastSkyfarer.EditorTools
{
    public static class StoryBotRunner
    {
        [MenuItem("Last Skyfarer/Run Story Bot")]
        public static void Run()
        {
            var bot = new StoryBot();
            bot.Run();
            foreach (string line in bot.Log) Debug.Log(line);
            string report = Path.GetFullPath("../StoryBotReport.txt");
            File.WriteAllLines(report, bot.Log);
            Debug.Log("LS_STORYBOT report " + report);
            if (Application.isBatchMode) EditorApplication.Exit(bot.AllPassed ? 0 : 1);
        }
    }
}

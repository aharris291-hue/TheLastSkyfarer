// The Last Skyfarer: player input (Input System), keyboard/mouse and gamepad, built in code so it needs no asset.
// Matches the Unreal bindings: WASD/stick move, mouse/right stick look, Space/A jump and glide, Shift/L3 sprint,
// Ctrl walk toggle and air brake (B), E/X interact, J journal, Esc/P pause, T peek objective, Q compass, M map.
using UnityEngine;
using UnityEngine.InputSystem;

namespace LastSkyfarer.Player
{
    public class PlayerInputs : System.IDisposable
    {
        public readonly InputAction Move, Look, Jump, Sprint, WalkToggle, AirBrake, Interact, Journal, Pause, Peek, Compass, Map;

        // Scripted input for automated checks: when set, these override the devices.
        public Vector2? ScriptedMove;
        public Vector2? ScriptedLook;

        public PlayerInputs()
        {
            Move = new InputAction("Move", InputActionType.Value);
            Move.AddCompositeBinding("2DVector").With("Up", "<Keyboard>/w").With("Down", "<Keyboard>/s").With("Left", "<Keyboard>/a").With("Right", "<Keyboard>/d");
            Move.AddCompositeBinding("2DVector").With("Up", "<Keyboard>/upArrow").With("Down", "<Keyboard>/downArrow").With("Left", "<Keyboard>/leftArrow").With("Right", "<Keyboard>/rightArrow");
            Move.AddBinding("<Gamepad>/leftStick");
            Look = new InputAction("Look", InputActionType.Value);
            Look.AddBinding("<Mouse>/delta").WithProcessor("scaleVector2(x=0.08,y=0.08)");
            Look.AddBinding("<Gamepad>/rightStick").WithProcessor("scaleVector2(x=2.4,y=2.4)");
            Jump = Button("Jump", "<Keyboard>/space", "<Gamepad>/buttonSouth");
            Sprint = Button("Sprint", "<Keyboard>/leftShift", "<Gamepad>/leftStickPress");
            WalkToggle = Button("WalkToggle", "<Keyboard>/leftCtrl", null);
            AirBrake = Button("AirBrake", "<Keyboard>/leftCtrl", "<Gamepad>/buttonEast");
            Interact = Button("Interact", "<Keyboard>/e", "<Gamepad>/buttonWest");
            Journal = Button("Journal", "<Keyboard>/j", "<Gamepad>/select");
            Pause = Button("Pause", "<Keyboard>/escape", "<Gamepad>/start");
            Pause.AddBinding("<Keyboard>/p");
            Peek = Button("Peek", "<Keyboard>/t", "<Gamepad>/dpad/down");
            Compass = Button("Compass", "<Keyboard>/q", "<Gamepad>/buttonNorth");
            Map = Button("Map", "<Keyboard>/m", "<Gamepad>/dpad/up");
        }

        static InputAction Button(string name, string key, string pad)
        {
            var a = new InputAction(name, InputActionType.Button);
            if (key != null) a.AddBinding(key);
            if (pad != null) a.AddBinding(pad);
            return a;
        }

        InputAction[] AllActions => new[] { Move, Look, Jump, Sprint, WalkToggle, AirBrake, Interact, Journal, Pause, Peek, Compass, Map };
        public void Enable() { foreach (var a in AllActions) a.Enable(); }
        public void Disable() { foreach (var a in AllActions) a.Disable(); }
        public void Dispose() { foreach (var a in AllActions) a.Dispose(); }

        public Vector2 MoveValue => ScriptedMove ?? Vector2.ClampMagnitude(Move.ReadValue<Vector2>(), 1f);
        public Vector2 LookValue => ScriptedLook ?? Look.ReadValue<Vector2>();
    }
}

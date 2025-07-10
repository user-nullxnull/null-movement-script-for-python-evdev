import evdev
from evdev import InputDevice, UInput, ecodes

# Find the keyboard device
kbd = None
for path in evdev.list_devices():
    dev = InputDevice(path)
    if 'keyboard' in dev.name.lower():
        kbd = dev
        break

if kbd is None:
    print("Keyboard not found")
    exit(1)

# Grab the keyboard to capture its events exclusively
kbd.grab()

# Create a uinput device to inject modified events
ui = UInput.from_device(kbd, name="virtual-keyboard")

# Initialize state variables
physical_state = {ecodes.KEY_A: False, ecodes.KEY_D: False, ecodes.KEY_W: False, ecodes.KEY_S: False}
sending_state = {ecodes.KEY_A: False, ecodes.KEY_D: False, ecodes.KEY_W: False, ecodes.KEY_S: False}
last_strafe_press = None  # Tracks last pressed key for A/D pair
last_forward_back_press = None  # Tracks last pressed key for W/S pair

try:
    for event in kbd.read_loop():
        if event.type == ecodes.EV_KEY and event.code in physical_state:
            key = event.code
            # Update physical state (1 = down, 0 = up, 2 = repeat)
            if event.value in (1, 2):  # Key down or repeat
                physical_state[key] = True
                if event.value == 1:  # Only update last pressed on initial press
                    if key in (ecodes.KEY_A, ecodes.KEY_D):
                        last_strafe_press = key
                    elif key in (ecodes.KEY_W, ecodes.KEY_S):
                        last_forward_back_press = key
            elif event.value == 0:  # Key up
                physical_state[key] = False

            # Determine desired sending state for A/D (strafe)
            desired_sending = sending_state.copy()
            if physical_state[ecodes.KEY_A] and physical_state[ecodes.KEY_D]:
                if last_strafe_press == ecodes.KEY_A:
                    desired_sending[ecodes.KEY_A] = True
                    desired_sending[ecodes.KEY_D] = False
                else:
                    desired_sending[ecodes.KEY_A] = False
                    desired_sending[ecodes.KEY_D] = True
            else:
                desired_sending[ecodes.KEY_A] = physical_state[ecodes.KEY_A]
                desired_sending[ecodes.KEY_D] = physical_state[ecodes.KEY_D]

            # Determine desired sending state for W/S (forward/back)
            if physical_state[ecodes.KEY_W] and physical_state[ecodes.KEY_S]:
                if last_forward_back_press == ecodes.KEY_W:
                    desired_sending[ecodes.KEY_W] = True
                    desired_sending[ecodes.KEY_S] = False
                else:
                    desired_sending[ecodes.KEY_W] = False
                    desired_sending[ecodes.KEY_S] = True
            else:
                desired_sending[ecodes.KEY_W] = physical_state[ecodes.KEY_W]
                desired_sending[ecodes.KEY_S] = physical_state[ecodes.KEY_S]

            # Inject events only if sending state changes
            for k in [ecodes.KEY_A, ecodes.KEY_D, ecodes.KEY_W, ecodes.KEY_S]:
                if desired_sending[k] != sending_state[k]:
                    ui.write(ecodes.EV_KEY, k, 1 if desired_sending[k] else 0)
                    ui.syn()
                    sending_state[k] = desired_sending[k]
                    print(f"Injected {k} {'down' if desired_sending[k] else 'up'}")  # Debug output
        else:
            # Pass through all other events unchanged
            ui.write(event.type, event.code, event.value)
            ui.syn()
except KeyboardInterrupt:
    print("Exiting script")
finally:
    kbd.ungrab()
    ui.close()

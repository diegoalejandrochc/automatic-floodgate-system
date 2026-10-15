# Team members: Diego Chuquillanqui, Diane Ngo, Artur Kis
# Purpose: Control an automatic floodgate system using a commercial rain
# sensor and a custom PEDOT:PSS humidity sensor. Either sensor can close
# the gate. LEDs report system status and a pushbutton reopens the gate
# after direct water is no longer detected.
# Started: 09/27/2026
# Last update: 10/01/2026
# AI use: ChatGPT assisted with code integration, troubleshooting, and
# organization. Physical construction, wiring, testing, measurements, and
# design decisions were completed and evaluated by the project team.

from machine import ADC, Pin
from time import sleep, sleep_us, ticks_diff, ticks_ms


# ==================================================
# INPUTS
# ==================================================

# Custom PEDOT:PSS humidity sensor
# A2 = GPIO 3
pedot_sensor = ADC(Pin(3))
pedot_sensor.atten(ADC.ATTN_11DB)

# Commercial rain sensor
# A5 = GPIO 12
rain_sensor = ADC(Pin(12))
rain_sensor.atten(ADC.ATTN_11DB)

# Manual reset button
# A7 = GPIO 14; PULL_UP means 1 = released, 0 = pressed
reset_button = Pin(14, Pin.IN, Pin.PULL_UP)


# ==================================================
# OUTPUTS
# ==================================================

red_led = Pin(5, Pin.OUT)    # D2: unsafe condition / gate closed
green_led = Pin(6, Pin.OUT)  # D3: safe condition / gate open


# ==================================================
# STEPPER MOTOR
# ==================================================

motor_pins = [
    Pin(7, Pin.OUT),
    Pin(8, Pin.OUT),
    Pin(9, Pin.OUT),
    Pin(10, Pin.OUT),
]

# Half-step sequence for the 28BYJ-48 through a ULN2003 driver.
sequence = [
    (1, 0, 0, 0),
    (1, 1, 0, 0),
    (0, 1, 0, 0),
    (0, 1, 1, 0),
    (0, 0, 1, 0),
    (0, 0, 1, 1),
    (0, 0, 0, 1),
    (1, 0, 0, 1),
]


# ==================================================
# CONTROL SETTINGS
# ==================================================

# Rain sensor: dry is near 65535; lower readings indicate more water.
RAIN_THRESHOLD = 35000

# PEDOT:PSS trigger and recovery thresholds relative to the startup baseline.
PEDOT_TRIGGER_PERCENT = 25
PEDOT_REARM_PERCENT = 10
PEDOT_REQUIRED_READINGS = 8
PEDOT_REARM_READINGS = 8

# Gate movement settings.
GATE_TRAVEL_STEPS = 7000
STEP_DELAY_US = 900
MAX_MOTOR_TIME_MS = 8000
CLOSE_DIRECTION = -1


# ==================================================
# MOTOR FUNCTIONS
# ==================================================

def apply_step(step):
    """Send one half-step pattern to the motor driver."""
    for pin, value in zip(motor_pins, step):
        pin.value(value)


def motor_off():
    """Remove power from all stepper outputs."""
    for pin in motor_pins:
        pin.off()


def move(steps, direction):
    """Move the stepper while enforcing a maximum run time."""
    start_time = ticks_ms()
    completed_steps = 0

    try:
        for i in range(steps):
            if ticks_diff(ticks_ms(), start_time) >= MAX_MOTOR_TIME_MS:
                print("!!! MOTOR SAFETY STOP !!!")
                print("Maximum motor run time reached.")
                break

            if direction == 1:
                step = sequence[i % 8]
            else:
                step = sequence[7 - (i % 8)]

            apply_step(step)
            sleep_us(STEP_DELAY_US)
            completed_steps += 1
    finally:
        motor_off()

    return completed_steps


def close_gate():
    """Move the gate in the closing direction."""
    print()
    print(">>> CLOSING GATE")
    completed = move(GATE_TRAVEL_STEPS, CLOSE_DIRECTION)
    print("Steps completed:", completed)
    print(">>> GATE CLOSED")
    print()


def open_gate():
    """Move the gate in the opening direction."""
    print()
    print(">>> OPENING GATE")
    completed = move(GATE_TRAVEL_STEPS, -CLOSE_DIRECTION)
    print("Steps completed:", completed)
    print(">>> GATE OPEN")
    print()


# ==================================================
# PEDOT:PSS CALIBRATION
# ==================================================

def calibrate_pedot_sensor():
    """Average dry readings to establish the startup PEDOT:PSS baseline."""
    print()
    print("Calibrating PEDOT:PSS sensor...")
    print("KEEP THE SENSOR DRY")
    print()

    samples = 20
    total = 0

    for i in range(samples):
        value = pedot_sensor.read_u16()
        total += value
        print("Calibration sample", i + 1, ":", value)
        sleep(0.1)

    baseline = total / samples

    print()
    print("PEDOT:PSS dry baseline:", baseline)
    print()

    return baseline


pedot_baseline = calibrate_pedot_sensor()


# ==================================================
# INITIAL STATE
# ==================================================

gate_closed = False
motor_busy = False
pedot_armed = True
pedot_trigger_count = 0
pedot_rearm_count = 0
previous_button = 1

red_led.off()
green_led.on()

print("Automatic floodgate system started")
print("Gate should begin physically OPEN")
print()


# ==================================================
# MAIN LOOP
# ==================================================

while True:
    pedot_value = pedot_sensor.read_u16()
    rain_value = rain_sensor.read_u16()
    current_button = reset_button.value()

    # Commercial rain sensor remains active continuously.
    rain_detected = rain_value < RAIN_THRESHOLD

    # Compare the PEDOT:PSS reading with its dry startup baseline.
    if pedot_baseline > 0:
        pedot_percent_change = (
            abs(pedot_value - pedot_baseline) / pedot_baseline
        ) * 100
    else:
        pedot_percent_change = 0

    pedot_detected = False

    # The PEDOT:PSS sensor triggers once, then waits for recovery before re-arming.
    if pedot_armed:
        if pedot_percent_change >= PEDOT_TRIGGER_PERCENT:
            pedot_trigger_count += 1
        else:
            pedot_trigger_count = 0

        if pedot_trigger_count >= PEDOT_REQUIRED_READINGS:
            pedot_detected = True
            pedot_armed = False
            pedot_rearm_count = 0
    else:
        pedot_trigger_count = 0

        if pedot_percent_change <= PEDOT_REARM_PERCENT:
            pedot_rearm_count += 1
        else:
            pedot_rearm_count = 0

        if pedot_rearm_count >= PEDOT_REARM_READINGS:
            pedot_armed = True
            pedot_rearm_count = 0
            print(">>> PEDOT:PSS SENSOR RE-ARMED")

    # Either sensor can automatically close the gate.
    close_condition = rain_detected or pedot_detected

    if close_condition and not gate_closed and not motor_busy:
        gate_closed = True
        motor_busy = True

        red_led.on()
        green_led.off()

        print()
        print("!!! MOISTURE WARNING !!!")

        if rain_detected:
            print("Rain sensor triggered")

        if pedot_detected:
            print("PEDOT:PSS sensor triggered")

        close_gate()
        motor_busy = False

    # Register only the transition from released to pressed.
    button_pressed = current_button == 0 and previous_button == 1

    if gate_closed and button_pressed and not motor_busy:
        # The rain sensor must be dry before the gate can reopen. The PEDOT:PSS
        # sensor may still be recovering and is temporarily kept disarmed.
        if not rain_detected:
            print("Reset accepted")

            pedot_armed = False
            pedot_trigger_count = 0
            pedot_rearm_count = 0

            motor_busy = True
            open_gate()
            gate_closed = False
            motor_busy = False

            red_led.off()
            green_led.on()
        else:
            print("Cannot reset: rain sensor still detects water")

    previous_button = current_button

    gate_status = "CLOSED" if gate_closed else "OPEN"

    print(
        "PEDOT:", pedot_value,
        "| Baseline:", round(pedot_baseline),
        "| Change:", round(pedot_percent_change, 2), "%",
        "| Armed:", pedot_armed,
        "| Rain:", rain_value,
        "| Rain Trigger:", rain_detected,
        "| Gate:", gate_status,
    )

    sleep(0.25)

# Purpose: Test the 28BYJ-48 stepper motor in both directions before integration.

from machine import Pin
from time import sleep_ms, sleep_us

IN1=Pin(7,Pin.OUT); IN2=Pin(8,Pin.OUT); IN3=Pin(9,Pin.OUT); IN4=Pin(10,Pin.OUT)
motor_pins=[IN1,IN2,IN3,IN4]
sequence=[(1,0,0,0),(1,1,0,0),(0,1,0,0),(0,1,1,0),(0,0,1,0),(0,0,1,1),(0,0,0,1),(1,0,0,1)]

def apply_step(step):
    for pin,value in zip(motor_pins,step): pin.value(value)

def move(steps,direction):
    for i in range(steps):
        step=sequence[i%8] if direction==1 else sequence[7-(i%8)]
        apply_step(step); sleep_us(700)

def motor_off():
    for pin in motor_pins: pin.off()

print('Moving direction 1'); move(16384,1); motor_off(); sleep_ms(1000)
print('Moving direction -1'); move(16384,-1); motor_off(); print('Motor test complete')

# Purpose: Read the commercial rain sensor and compare dry and wet ADC values.

from machine import Pin, ADC
from time import sleep

rain_sensor=ADC(Pin(12))
rain_sensor.atten(ADC.ATTN_11DB)

print('Rain sensor test started')
while True:
    print('Rain sensor ADC:', rain_sensor.read_u16())
    sleep(0.5)

# Purpose: Measure the homemade PEDOT:PSS sensor relative to a dry baseline.

from machine import Pin, ADC
from time import sleep

pedot=ADC(Pin(3)); pedot.atten(ADC.ATTN_11DB)
print('Keep PEDOT:PSS sensor dry during calibration')
total=0; samples=20
for i in range(samples):
    value=pedot.read_u16(); total+=value
    print('Calibration sample',i+1,':',value); sleep(0.1)
baseline=total/samples
print('Dry baseline:',baseline)

while True:
    value=pedot.read_u16()
    delta=value-baseline
    pct=(abs(delta)/baseline)*100 if baseline>0 else 0
    print('PEDOT:',value,'| Baseline:',round(baseline),'| Delta:',round(delta),'| Change:',round(pct,2),'%')
    sleep(0.25)

from machine import UART, Pin

led = Pin(25, Pin.OUT)

uart = UART(0,baudrate=115200,tx=Pin(0),rx=Pin(1),bits=8,parity=None,stop=1)

while True:
    if not uart.any():
        continue
    value = uart.read(4)
    if value[3] != 255:
        v = uart.read(1)
        continue
    print(value)
    uart.write(value)
    if value[2] == 1:
        led.value(1)
    else:
        led.value(0)
    

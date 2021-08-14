from machine import UART, Pin, ADC
#hello
led = Pin(25, Pin.OUT)
led_state = False
sensor_temp = ADC(4)

uart = UART(0,baudrate=115200,tx=Pin(0),rx=Pin(1),bits=8,parity=None,stop=1)

while True:
    if not uart.any():
        continue
    value = uart.read(4)
    if len(value) != 4:
        uart.read(1)
        continue
    # all packets are of the 4 byte format [code, d1, d2, 255]
    if value[3] != 255:
        # not synchronised, read one byte and continue
        uart.read(1)
        continue

    # [1, 25, 1, 255] and [1, 25, 0, 255] are turning led on/off
    if (value[0] == 1) and (value[1] == 25):
        # set the led and send the new led state right back
        uart.write(value)
        if value[2] == 1:
            led.value(1)
            led_state = True
        else:
            led.value(0)
            led_state = False
        continue

    # [2, 25, 0, 255] requests current led state
    if (value[0] == 2) and (value[1] == 25):
        # get the led state and send back
        if led_state:
            uart.write(bytes([2, 25, 1, 255]))
        else:
            uart.write(bytes([2, 25, 0, 255]))
        continue

    # [3, 0, n, 255] is a monitoring packet, the pi expects it to be echoed back
    if (value[0] == 3) and (value[1] == 0):
        # echo the value back
        uart.write(value)
        continue

    # [5, 4, 0, 255] is a request for temperature
    if (value[0] == 5) and (value[1] == 4):
        reading = sensor_temp.read_u16()
        # create data of [5,d1,d2,255]
        data = [5] + list(reading.to_bytes(2,'big')) + [255]
        uart.write(bytes(data))


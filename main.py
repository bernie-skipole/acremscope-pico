from machine import UART, Pin, ADC, Timer

import motorcurve

led = Pin(25, Pin.OUT)
led_state = False
sensor_temp = ADC(4)

uart = UART(0,baudrate=115200,tx=Pin(0),rx=Pin(1),bits=8,parity=None,stop=1)

# get the two doors

pins0 = {'direction':?, 'pwm':?, 'limit_close':?, 'limit_open':}

_DOOR0 = motorcurve.DoorMotor( direction=?, pwm=?, limit_close=?, limit_open=? )
_DOOR1 = motorcurve.DoorMotor( direction=?, pwm=?, limit_close=?, limit_open=? )

# start with both doors in an uknown status
_DOOR0_STATUS = 0
_DOOR1_STATUS = 0


def read_uart():
    """Read an instruction from the Raspberry pi via UART
    Handle an LED request, temerature request, door status request
    Return None, or (code, d1, d2)"""
    global led_state
    if not uart.any():
        return
    value = uart.read(4)
    if len(value) != 4:
        return
    # all packets are of the 4 byte format [code, d1, d2, 255]
    if value[3] != 255:
        # not synchronised, read one byte and continue
        uart.read(1)
        return

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
        return

    # [2, 25, 0, 255] requests current led state
    if (value[0] == 2) and (value[1] == 25):
        # get the led state and send back
        if led_state:
            uart.write(bytes([2, 25, 1, 255]))
        else:
            uart.write(bytes([2, 25, 0, 255]))
        return

    # [3, 0, n, 255] is a monitoring packet, the pi expects it to be echoed back
    if (value[0] == 3) and (value[1] == 0):
        # echo the value back
        uart.write(value)
        return

    # [5, 4, 0, 255] is a request for temperature
    if (value[0] == 5) and (value[1] == 4):
        reading = sensor_temp.read_u16()
        # create data of [5,d1,d2,255]
        data = [5] + list(reading.to_bytes(2,'big')) + [255]
        uart.write(bytes(data))
        return

    # [6, 1, N, 255] is a request for status for door number N, where N is 0 or 1
    if (value[0] == 6) and (value[1] == 1):
        # create data of [7,N,code,255]
        if value[2]:
            # motor1
            data = [7, 1, _DOOR1.status(),255]
        else:
            # motor0  
            data = [7, 0, _DOOR0.status(),255]
        uart.write(bytes(data))
        return

    # so, not LED, temperature, door status or monitoring, return the code received
    return value[:3]


def report_door_change():
    "Report back if a door has changed status"
    global _DOOR0_STATUS, _DOOR1_STATUS
    # motor0
    status0 = _DOOR0.status()
    if status0 != _DOOR0_STATUS:
        _DOOR0_STATUS = status0
        uart.write(bytes([7, 0, status0, 255]))
    # motor1
    status1 = _DOOR1.status()
    if status1 != _DOOR1_STATUS:
        _DOOR1_STATUS = status1
        uart.write(bytes([7, 1, status1, 255]))


while True:
    # check for incoming uart data
    rxd = read_uart()
    # if door status has changed, report it back
    report_door_change()
    # operate the doors
    _DOOR0.run()
    _DOOR1.run()
    if rxd is None:
        # No further requests from the pi have been received, so loop back and check again
        continue
    # [8, N, 0] is a request to open the door N (N is 0 or 1 for door 0 or door 1)
    if rxd[0] == 8 and rxd[2] == 0:
        # open a door
        if rxd[1]:
            # motor 1
            _DOOR1.open()
        else:
            # motor 0
            _DOOR0.open()
    # [8, N, 1] is a request to close the door N (N is 0 or 1 for door 0 or door 1)
    if rxd[0] == 8 and rxd[2] == 1:
        # close a door
        if rxd[1]:
            # motor 1
            _DOOR1.close()
        else:
            # motor 0
            _DOOR0.close()
    # [9, 0, 0] is a request to open both doors
    if rxd[0] == 9 and rxd[2] == 0:
        _DOOR0.open()
        _DOOR1.open()
    # [9, 0, 1] is a request to close both doors
    if rxd[0] == 9 and rxd[2] == 1:
       _DOOR0.close()
       _DOOR1.close()
 





from machine import UART, Pin, ADC, Timer

import motors

# set up the two doors, with the appropriate pico pins

_DOOR0 = motors.Motor( "Left", direction=14, pwm=15, limit_close=12, limit_open=13 )
_DOOR1 = motors.Motor( "Right", direction=17, pwm=16, limit_close=19, limit_open=18 )

led = Pin(25, Pin.OUT)
led_state = False
sensor_temp = ADC(4)

uart = UART(0,baudrate=115200,tx=Pin(0),rx=Pin(1),bits=8,parity=None,stop=1)


def read_uart():
    """Read an instruction from the Raspberry pi via UART
    Return None, or [code, d1, d2]"""
    if not uart.any():
        return
    value = uart.read(4)
    # all packets received are of the 4 byte format [code, d1, d2, 255]
    if len(value) != 4:
        return
    if value[3] != 255:
        # not synchronised, read one byte and continue
        uart.read(1)
        return
    # so, remove the 255 and return [code, d1, d2]
    return value[:3]


def write_uart(code, d1, d2):
    """Write the code, d1 and d2 to the UART"""
    uart.write(bytes([code, d1, d2, 255]))



while True:
    # check for incoming uart data
    rxd = read_uart()

    # check motor limits, this stops the door if a limit has been reached regardless
    # of any pwm value received from pi
    _DOOR0.checklimits()
    _DOOR1.checklimits()

    if rxd is None:
        # No further requests from the pi have been received, so loop back and check again
        continue
    code, d1, d2 = rxd

    # [1, 25, 1] and [1, 25, 0] are turning led on/off
    if code == 1:
        if d1 == 25:
            # set the led and send the new led state right back
            if d2 == 1:
                led.value(1)
                led_state = True
                write_uart(1, 25, 1)
            else:
                led.value(0)
                led_state = False
                write_uart(1, 25, 0)
        continue

    # [2, 25, 0] requests current led state
    if code == 2:
        if d1 == 25:
            # get the led state and send back
            if led_state:
                write_uart(2, 25, 1)
            else:
                write_uart(2, 25, 0)
        continue

    # [3, 0, n] is a monitoring packet, the pi expects it to be echoed back
    if code == 3:
        if d1 == 0:
            # echo the value back
            write_uart(3, 0, d2)
        continue

    # [5, 4, 0] is a request for temperature
    if code == 5:
        if d1 == 4:
            try:
                reading = sensor_temp.read_u16()
                # create data of [5,two bytes temperature]
                data = [5] + list(reading.to_bytes(2,'big'))
                write_uart(*data)
            except:
                pass
        continue

    # [16, 0, pwm] sets pwm on door0 (left)
    # [16, 1, pwm] sets pwm on door1 (right)
    if code == 16:
        if d1:
            _DOOR1.pwm_ratio = d2
        else:
            _DOOR0.pwm_ratio = d2
        continue

    # [17, 0, 0] sets door0 to direction 0 (1 for open, 0 for close)
    if code == 17:
        if d1:
            # door 1
            if d2:
                _DOOR1.direction_open()
            else:
                _DOOR1.direction_close()
        else:
            # door 0
            if d2:
                _DOOR0.direction_open()
            else:
                _DOOR0.direction_close()





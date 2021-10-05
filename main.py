from machine import UART, Pin, ADC, Timer

import motorcurve

# set up the two doors, with the appropriate pico pins

_DOOR0 = motorcurve.DoorMotor( "Left", direction=14, pwm=15, limit_close=12, limit_open=13 )
_DOOR1 = motorcurve.DoorMotor( "Right", direction=17, pwm=16, limit_close=19, limit_open=18 )

led = Pin(25, Pin.OUT)
led_state = False
sensor_temp = ADC(4)

uart = UART(0,baudrate=115200,tx=Pin(0),rx=Pin(1),bits=8,parity=None,stop=1)

# On startup get the door status

_DOOR0_STATUS = _DOOR0.status()
_DOOR1_STATUS = _DOOR1.status()


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


def report_door_change():
    "Update door status globals, and report back if a door has changed status"
    global _DOOR0_STATUS, _DOOR1_STATUS
    # motor0
    status0 = _DOOR0.status()
    if status0 != _DOOR0_STATUS:
        _DOOR0_STATUS = status0
        write_uart(7, 0, status0)
    # motor1
    status1 = _DOOR1.status()
    if status1 != _DOOR1_STATUS:
        _DOOR1_STATUS = status1
        write_uart(7, 1, status1)


# write the initial door status to the uart

write_uart(7, 0, _DOOR0_STATUS)
write_uart(7, 1, _DOOR1_STATUS)


while True:
    # check for incoming uart data
    rxd = read_uart()
    # update door status, and if it has changed, report it back
    report_door_change()
    # operate the doors
    _DOOR0.run()
    _DOOR1.run()
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

    # [6, 1, N] is a request for status for door number N, where N is 0 or 1
    # return the door status code
    if code == 6:
        if d1 == 1:
            # create data of [7,N,code]
            if d2:
                # motor1
                write_uart(7, 1, _DOOR1.status())
            else:
                # motor0  
                write_uart(7, 0, _DOOR0.status())
        continue

    # [8, N, 0] is a request to open the door N (N is 0 or 1 for door 0 or door 1)
    # [8, N, 1] is a request to close the door N
    if code == 8:
        if d1:
            # motor 1
            if d2:
                _DOOR1.close()
            else:
                _DOOR1.open()
        else:
            # motor 0
            if d2:
                _DOOR0.close()
            else:
                _DOOR0.open()
        continue

    # [9, 0, 0] is a request to open both doors
    # [9, 0, 1] is a request to close both doors
    if code == 9:
        if d1 == 0:
            if d2:
                _DOOR0.close()
                _DOOR1.close()
            else:
                _DOOR0.open()
                _DOOR1.open()
        continue

    # [10 for door 0
    if code == 10:
        if d1 == 1:
            # fast duration
            _DOOR0.fast_duration =  d2
            # write status back
            write_uart(12, 1, d2)
        if d1 == 2:
            # duration
            _DOOR0.duration =  d2
            # write status back
            write_uart(12, 2, d2)
        if d1 == 3:
            # max_running_time
            _DOOR0.max_running_time = d2
            # write status back
            write_uart(12, 3, d2)
        if d1 == 4:
            # maximum ratio * 100
            mr = d2 / 100
            _DOOR0.maximum = mr
            # write status back
            write_uart(12, 4, d2)
        if d1 == 5:
            # minimum ratio * 100
            mr = d2 / 100
            _DOOR0.minimum = mr
            # write status back
            write_uart(12, 5, d2)
        continue

    # [11 for door 1
    if code == 11:
        if d1 == 1:
            # fast duration
            _DOOR1.fast_duration =  d2
            # write status back
            write_uart(13, 1, d2)
        if d1 == 2:
            # duration
            _DOOR1.duration =  d2
            # write status back
            write_uart(13, 2, d2)
        if d1 == 3:
            # max_running_time
            _DOOR1.max_running_time = d2
            # write status back
            write_uart(13, 3, d2)
        if d1 == 4:
            # maximum ratio * 100
            mr = d2 / 100
            _DOOR1.maximum = mr
            # write status back
            write_uart(13, 4, d2)
        if d1 == 5:
            # minimum ratio * 100
            mr = d2 / 100
            _DOOR1.minimum = mr
            # write status back
            write_uart(13, 5, d2)
        continue

    # [12 requests for door 0
    if code == 12:
        if d1 == 1:
            # fast duration
            write_uart(12, 1, _DOOR0.fast_duration)
        if d1 == 2:
            # duration
            write_uart(12, 2, _DOOR0.duration)
        if d1 == 3:
            # max_running_time
            write_uart(12, 3, _DOOR0.max_running_time)
        if d1 == 4:
            # maximum ratio * 100
            write_uart(12, 4, int(_DOOR0.maximum * 100))
        if d1 == 5:
            # minimum ratio * 100
            write_uart(12, 5, int(_DOOR0.minimum * 100))
        continue

    # [13 requests for door 1
    if code == 13:
        if d1 == 1:
            # fast duration
            write_uart(13, 1, _DOOR1.fast_duration)
        if d1 == 2:
            # duration
            write_uart(13, 2, _DOOR1.duration)
        if d1 == 3:
            # max_running_time
            write_uart(13, 3, _DOOR1.max_running_time)
        if d1 == 4:
            # maximum ratio * 100
            write_uart(13, 4, int(_DOOR1.maximum * 100))
        if d1 == 5:
            # minimum ratio * 100
            write_uart(13, 5, int(_DOOR1.minimum * 100))
        continue



        

 





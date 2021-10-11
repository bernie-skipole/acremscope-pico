

from machine import Pin, PWM

import time

class Motor():

    def __init__(self, name, direction, pwm, limit_close, limit_open):
        "name is for possile debugging, other arguments are the pico pins"

        self.name = name

        # set direction pin output
        self.direction_pin = Pin(direction, Pin.OUT)
        self.direction_pin.value(0)
        self._direction = 0
        
        # set pwm, with frequency 500, duty 0 to ensure it starts stopped
        self.pwm = PWM(Pin(pwm))
        # Set the PWM frequency.
        self.pwm.freq(500)
        # ensure the motor is stopped
        self._pwm_ratio = 0
        self.pwm.duty_u16(0)

        # set limit pins
        self.limit_close = Pin(limit_close, Pin.IN, Pin.PULL_UP)
        self.limit_open = Pin(limit_open, Pin.IN, Pin.PULL_UP)

        # An attribute to hold a millisecond time value, used to ensure door does not run continuously
        self.start_time = None


    @property
    def pwm_ratio(self):
        return self._pwm_ratio

    @pwm_ratio.setter
    def pwm_ratio(self, value):
        "Set the pwm ratio on the pwm pin"
        # has this changed from previous?
        if value == self._pwm_ratio:
            # no change from the last time this was set, no need to apply this to the pwm pin
            return
        if self.checklimits():
            return
        # so limits not reached, set a value
        self._pwm_ratio = value
        # value is a percentage, divide by 100 to give 1-0 range, then multiply by 65536 for bit value
        self.pwm.duty_u16(int(value*655.36))

    def direction_open(self):
        self.direction_pin.value(1)
        self._direction = 1

    def direction_close(self):
        self.direction_pin.value(0)
        self._direction = 0

    def checklimits(self):
        "If limit switch, or door timer, demands a stop, set pwm to zero and return a True"
        # set self.start_time if door has started moving
        self.start_timer()

        if self.start_time is not None:
            # door is running
            delta = time.ticks_diff(time.ticks_ms(), self.start_time) # compute time difference, which is current running time
            if delta >= 120000:
                # running time is greater than 120 seconds, ie two minutes. So stop the door
                self._pwm_ratio = 0
                self.pwm.duty_u16(0)
                return True

        if self._direction and (not self.limit_open.value()):   # openning, but limit_open is low, so switch closed
            self._pwm_ratio = 0
            self.pwm.duty_u16(0)
            return True

        if (not self._direction) and (not self.limit_close.value()):   # closing, but limit_close is low, so switch closed
            self._pwm_ratio = 0
            self.pwm.duty_u16(0)
            return True

        return False

    def start_timer(self):
        if self._pwm_ratio == 0:
            # door stopped, reset timer
            self.start_time = None
        elif self.start_time is None:
            # pwm_ratio has been set, but not self.running_time
            self.start_time = time.ticks_ms() # get millisecond counter
            # self.start_time now stays at this untill self._pwm_ratio becomes zero




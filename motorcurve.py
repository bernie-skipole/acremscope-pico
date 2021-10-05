

import os

from machine import Timer, Pin, PWM

# create a global counter
_TICK = 0

tim = Timer()

def tick(timer):
    "Increment _TICK, and after 1000 seconds (10000 calls to this function), reset it to 0"
    global _TICK
    _TICK += 1
    if _TICK >= 10000:
        _TICK = 0
 
tim.init(freq=10, mode=Timer.PERIODIC, callback=tick)

# The default values in this class should be matched to the actual roof motors

class DoorMotor():


    def __init__(self, name, fast_duration=4, duration=8, max_running_time=10, maximum=0.95, minimum=0.05, **pins):
        """When self.run is called, sets a pmw ratio value between 0 and maximum for a given time since open or close were called,
           the defaults above should be tailored to the actual door and H bridge used.
           duration is the duration of the perod, after which the pmw value will be 'minimum'
           fast_duration is the period where the pmw value will be maximum
           max_running_time is the full duration, after which, the value will be zero and the open/close will be considered complete
           for example, if duration is 60, fast_duration is 40, max_running_time is 65
           then, for t seconds 0 to 10 the ratio will climb from 0 to maximum,
           then stay at maximum for t 10 to 50, (making 40 seconds of fast_duration)
           and then ramp down to minimum for t 50 to 60
           and 60 to 65 will stay at the minimum
           and beyond 65 will be zero"""

        self.name = name
        # this name is used as the file name where door parameters will be saved

        # pins is a dictionary of pin functions to GPIO pin numbers, the functions should be:
        # 'direction', 'pwm', 'limit_close', 'limit_open'

        # set direction pin output
        self.direction = Pin(pins['direction'], Pin.OUT)
        self.direction.value(0)

        # set pwm, with frequency 500, duty 0 to ensure it starts stopped
        self.pwm = PWM(Pin(pins['pwm']))
        # Set the PWM frequency.
        self.pwm.freq(500)
        # ensure the motor is stopped
        self.pwm.duty_u16(0)

        # set limit pins
        self.limit_close = Pin(pins['limit_close'], Pin.IN, Pin.PULL_UP)
        self.limit_open = Pin(pins['limit_open'], Pin.IN, Pin.PULL_UP)

        # status codes
        # 0 : unknown - initial start up value
        # 1 : open
        # 2 : opening
        # 3 : closed
        # 4 : closing
        # 5 : Error - believed open, but limit switch has not closed
        # 6 : Error - believed closed, but limit switch has not closed
        # 7 : Error - both limit switches are closed

        self._status = 0
        self.start_running = 0
        self.pwm_ratio = 0

        # The slow_close is set True when the door is being closed from an unknown position,
        # if True it sets the maximum speed to minimum + 0.01, ie just above minimum
        self.slow_close = False

        # Set these parameters to default
        self._fast_duration = fast_duration
        self._duration = duration
        self._max_running_time = max_running_time
        self._maximum = maximum
        self._minimum = minimum

        # If new values have been set in a file, read them
        self.read_parameters()


    def read_parameters(self):
        """Reads the parameters from a file"""
        if self.name not in os.listdir():
            return
        f = open(self.name, "r")
        parameter_strings = f.readlines()
        f.close()
        if len(parameter_strings) != 5:
            return
        parameter_list = [ int(p.strip()) for p in parameter_strings]
        self._fast_duration = parameter_list[0]
        self._duration = parameter_list[1]
        self._max_running_time = parameter_list[2]
        self._maximum = parameter_list[3]/100
        self._minimum = parameter_list[4]/100


    def write_parameters(self):
        """Saves the parameters to a file"""
        f = open(self.name, "w")
        parameter_list = [self._fast_duration, self._duration, self._max_running_time, int(self._maximum*100), int(self._minimum*100)]
        for p in parameter_list:
            f.write(str(p)+"\n")
        f.close()

    @property
    def fast_duration(self):
        return self._fast_duration

    @fast_duration.setter
    def fast_duration(self, value):
        "Set fast_duration, and adjust other values to be greater"
        if self._max_running_time <= value:
            self._max_running_time = value + 2
        if self._duration <= value:
            self._duration = value + 1
        self._fast_duration = value
        self.write_parameters()


    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, value):
        "Set duration, and adjust other values"
        if self._max_running_time <= value:
            self._max_running_time = value + 1
        self._duration = value
        if self._fast_duration >= value:
            self._fast_duration =  value-1
        self.write_parameters()

    @property
    def max_running_time(self):
        return self._max_running_time

    @max_running_time.setter
    def max_running_time(self, value):
        "Set max_running_time, and adjust other values"
        self._max_running_time = value
        if self._duration >= value:
            self._duration = value - 1
        if self._fast_duration >= self._duration:
            self._fast_duration =  self._duration-1
        self.write_parameters()

    @property
    def maximum(self):
        return self._maximum

    @maximum.setter
    def maximum(self, value):
        "Set maximum"
        if value > 0.95:
            self._maximum = 0.95
        elif value < 0.02:
            self._maximum = 0.02
        else:
            self._maximum = value
        if self._minimum >= self._maximum:
            self._minimum = self._maximum - 0.01
        self.write_parameters()

    @property
    def minimum(self):
        return self._minimum

    @minimum.setter
    def minimum(self, value):
        "Set minimum"
        if value <= 0:
            self._minimum = 0.01
        elif value > 0.5:
            self._minimum = 0.5
        else:
            self._minimum = value
        if self._maximum <= self._minimum:
            self._maximum = self._minimum+0.01
        self.write_parameters()

    def status(self):
        """Returns a status code 1 to 7"""

        if not self._status:
            # status is zero, the door is unknown
            # is it open or closed?
            if not self.limit_close.value():
                # Its low, so the limit_close switch is closed, putting a ground on the pin
                # set status  as closed
                self.slow_close = False
                self._status = 3
            elif not self.limit_open.value():
                # Its low, so the limit_open switch is closed, putting a ground on the pin
                # set status as open
                self.slow_close = False
                self._status = 1
            else:
                # if still unknown, try a forced close
                # change status to closing and run the motor slowly
                self.slow_close = True
                self._status = 4
                self.start_running = _TICK
                self.direction.value(0)


        ######## test lines
        if self._status == 6:
            self._status = 3
        if self._status == 5:
            self._status = 1
        ######################### remove above to enable limit switches

        return self._status

    def checkbothlimits(self):
        "Returns True if both limit sitches are closed, which is an invalid state"
        if self.limit_open.value() or self.limit_close.value():
            # one is open
            return False
        return True

    def open(self):
        if self._status != 3:
            # only a closed door can be opened
            return
        # change status to opening
        self._status = 2
        self.start_running = _TICK
        self.direction.value(1)
        

    def close(self):
        if self._status != 1:
            # only an open door can be closed
            return
        # change status to closing
        self._status = 4
        self.start_running = _TICK
        self.direction.value(0)


    def run(self):
        "Runs the motor"
        if self._status != 2 and self._status != 4:
            # the motor is not running
            return

        if self.checkbothlimits():
            # both limit switches are closed, invalid value, stop the door
            self.slow_close = False
            self._status = 7
            self.pwm_ratio = 0
            self.pwm.duty_u16(0)
            return

        if self._status == 2:
            # Its opening, check for limit switch
            if not self.limit_open.value():
                # Its low, so the limit_open switch is closed, putting a ground on the pin
                # flag the door as opened
                self.slow_close = False
                self._status = 1
                self.pwm_ratio = 0
                self.pwm.duty_u16(0)
                return

        if self._status == 4:
            # Its closing, check for limit switch
            if not self.limit_close.value():
                # Its low, so the limit_close switch is closed, putting a ground on the pin
                # flag the door as closed
                self.slow_close = False
                self._status = 3
                self.pwm_ratio = 0
                self.pwm.duty_u16(0)
                return

        
        if _TICK == self.start_running:
            # start the motor after the first _TICK
            # since at time zero, the pwm ratio should be zero
            # so return here, to give _TICK time to increment
            return            
 
        if _TICK > self.start_running:
            running_time = _TICK - self.start_running
        else:
            # _TICK must have reset to 0
            running_time = _TICK + 10000 - self.start_running
        # running time in tenths of a second, convert to seconds
        running_time = running_time/10.0
        # get pwm ratio


        # If the running time is greater than max allowed, somthing is possibly wrong
        # so stop the motor
        if running_time >= self._max_running_time:
            if self._status == 2:
                # was opening, so assume the door is now open 
                self._status = 1
                # confirm limit switch, if not set, an alert is needed
                if self.limit_open.value():
                    # Its high, so the limit_open switch is still open
                    # flag an error
                    self._status = 5
                else:
                    # Its low, limit_open switch is closed, all ok
                    self.slow_close = False
            if self._status == 4:
                # was closing, so assume the door is now closed
                self._status = 3
                # confirm limit switch, if not set, an alert is needed
                if self.limit_close.value():
                    # Its high, so the limit_close switch is still open
                    # flag an error
                    self._status = 6
                else:
                    # Its low, limit_close switch is closed, all ok
                    self.slow_close = False
            # and stop the motor
            pwm = 0
        else:
            # door is still opening or closing, get the pwm ratio
            pwm = pwmratio(running_time, self._fast_duration, self._duration, self._minimum)
        if pwm:
            # pwm is a number between 0 and 1, reduce the value so instead of 1 the maximum ratio is given
            if self.slow_close:
                # As a 'slow close' is requested, the maximum speed is set to just above minimum
                #maxratio = self._minimum + 0.01
                ###########################################
                # initially, until limit switches are working, ignore slow_close instruction
                maxratio = self._maximum
            else:
                maxratio = self._maximum
            if running_time<self._duration/2.0:
                # the start up, scale everything by maxratio, so 1 -> maxratio
                pwm = pwm*maxratio
            else:
                # the slow-down, scale 1 to be maxratio, but minimum stays as it is
                m = (maxratio-self._minimum)/(1-self._minimum)
                pwm = m*pwm + maxratio - m
        pwm = int(pwm*65536)
        # has this changed from previous?
        if pwm == self.pwm_ratio:
            # no change from the last time run was called, no need to apply this to the pwm pin
            return
        # so the pwm ratio has changed, set this onto the pwm pin
        self.pwm_ratio = pwm
        self.pwm.duty_u16(self.pwm_ratio)


def curve(t, duration, minimum=0.0):
    """Returns a value between 0 and 1.0 for a given t
       with an eight second acceleration and deceleration
       For t from 0 to 8 increases from 0 up to 1.0
       For t from duration-8 to duration decreases to minimum
       For t beyond duration, returns the minimum
       The minimum value is so that on reaching duration, where normally it would be stopping,
       the motor can continue in a go-slow mode until a limit switch actually stops the motor
       mimimum is a value between 0 and 0.5"""
    if minimum < 0:
        minimum = 0.0
    if minimum > 0.5:
        mimimum = 0.5
    if t >= duration:
        return minimum

    half = duration/2.0
    if t<=half:
        # for the first half of duration, increasing speed to a maximum of 1.0 after 8 seconds
        if t>8.0:
            return 1.0
        acceleration = True
    else:
        # for the second half of duration, decreasing speed to zero when there are 8 seconds left
        if duration-t>8.0:
            return 1.0
        t = 20 - (duration-t)
        acceleration = False

    # This curve is a fit increasing to 1 (or at least near to 1) with t from 0 to 8,
    # and decreasing with t from 12 to 20
    a = -0.0540937
    b = 0.330319
    c = -0.0383795
    d = 0.00218635
    e = -5.46589e-05
    y = a + b*t + c*t*t + d*t*t*t + e*t*t*t*t
    if y < 0.0:
        y = 0.0
    if y > 1.0:
        y = 1.0
    if acceleration or (not minimum) or (t<12):
        # If in the acceleration phase, or if minimum is zero, or if still not reached deceleration time, then return this value of y
        return round(y, 3)
    # A minimum has been specified
    # while decelerating, instead of decelerating to zero, decelerate to the minimum value
    # add a value k, derived from k = p*t + q
    # if t == 12 add nothing
    # if t == 20 add minimum
    p = minimum / 8.0
    q = -12*p
    k = p*t + q
    y = y+k
    if y < 0.0:
        y = 0.0
    if y > 1.0:
        y = 1.0
    return round(y, 3)


def pwmratio(t, fast_duration, duration, minimum=0.0):
    """Returns a value between 0 and 1.0 for a given t
       duration is the duration of the perod, after which the value returned is 'minimum'
       fast_duration is the period where the value returned will be 1
       for example, if duration is 60, and fast_duration is 40, then the ratio will climb from 0 to 1
       given a t of 0-10, then 1 for 10-50, and finally, ramp down to minimum for 50-60
       and beyond 60 will stay at the minimum
       The minimum value is so that on reaching duration, where normally it would be stopping,
       the motor can continue in a go-slow mode until a limit switch actually stops the motor
       mimimum is a value between 0 and 0.5"""
    if minimum < 0:
        minimum = 0.0
    if minimum > 0.5:
        mimimum = 0.5
    if t >= duration:
        return minimum
    if fast_duration >= duration:
        if t < duration:
            return 1
    # so t is less than duration
    # scale t and duration
    acc_time = (duration - fast_duration)/2.0
    scale = 8.0/acc_time
    # the value of 8.0 is used as the following call to curve
    # is set with an acceleration time of 8
    return curve(t*scale, duration*scale, minimum)



if __name__ == "__main__":

    codes = { 1 : "open",
              2 : "opening",
              3 : "closed",
              4 : "closing",
              5 : "Error - believed open, but limit switch has not closed",
              6 : "Error - believed closed, but limit switch has not closed",
              7 : "Error - both limit switches are closed" }

    # get a door
    _DOOR0 = DoorMotor( "Left", direction=14, pwm=15, limit_close=12, limit_open=13 )
    # open it
    print("CLOSE")
    _DOOR0.close()
    while True:
        # operate the doors
        _DOOR0.run()
        STATUS = _DOOR0.status()
        print(codes[STATUS], _DOOR0.pwm_ratio)
        if STATUS in [1, 3, 5, 6, 7]:
            # should be stopped
            break
    print("Changing max running time to 15")
    _DOOR0.max_running_time = 15
    print("OPEN")
    _DOOR0.open()
    while True:
        # operate the doors
        _DOOR0.run()
        STATUS = _DOOR0.status()
        print(codes[STATUS], _DOOR0.pwm_ratio)
        if STATUS in [1, 3, 5, 6, 7]:
            # should be stopped
            break

        
 



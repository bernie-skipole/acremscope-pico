# acremscope-pico
Part of the acremscope build

The pi and pico communicate by UART, connectivity is shown in the included diagram.

Commands are sent between the devices as three byte codes, with a terminating byte of 255, For example

code:         1

pin:         25

state:        1 or 0

terminator: 255

Bytes of (1,25,1,255) would turn pin 25, the LED on

Bytes of (1,25,0,255) would turn pin 25, the LED on

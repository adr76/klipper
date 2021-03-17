# Oled Controller Module Extra
# OLED 1.3"  I2C SH1106
# MCP23013 - 11 Keys, 5 Leds
# 
# Copyright (C) 2021  adr76 <Oleksandr.druz@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

# import pins
import os
import logging
from . import bus

MCP23017_ADDR = 0x20
MCP23017_SPEED = 100000

# MCP23017 Registers
IODIRA     = 0x00
IODIRB     = 0x01
GPINTENA   = 0x04
GPINTENB   = 0x05
DEFVALA    = 0x06
DEFVALB    = 0x07
INTCONA    = 0x08
INTCONB    = 0x09
IOCON      = 0x0A #0x0B is the same
GPPUA      = 0x0C
GPPUB      = 0x0D
INTFA      = 0x0E
INTFB      = 0x0F
INTCAPA    = 0x10
INTCAPB    = 0x11
GPIOA      = 0x12
GPIOB      = 0x13
OLATA      = 0x14
OLATB      = 0x15

GPIOA_DEF = 0x5f
GPIOB_DEF = 0x6d
GPIO_DEF = 0x5f6d

LED = {
    '1'     : 9, #blue
    '2'     : 12, #red
    '3'     : 15, #blue
    '4'     : 5, #green
    '5'     : 7 #yellow
}

KEYS = {
    '1'        : 0x1, # UP
    '21'       : 0x5, # F + UP 
    '2'        : 0x4, # F
    '23'       : 0xc, # F + Down
    '3'        : 0x8, # Down
    '4'        : 0x100, # Home
    '5'        : 0x200, # Light
    '6'        : 0x400, #key 6
    '7'        : 0x800, #key 7
    '8'        : 0x1000, #key 8
    '9'        : 0x20, # PSU/PowerOff(longPress)
    '10'       : 0x40, # Fan
    '11'       : 0x4000# Pause/Resume
}

MCP23017_REPORT_TIME = .5 #sec

# Klipper Log
# tail -f /tmp/klippy.log | grep -i -E "(mcp23017:|oled_controller.py|error)"
# tail -f /tmp/klippy.log | grep -i -E "(mcp23017:|error)
class mcp23017(object):
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.i2c = bus.MCU_I2C_from_config(config, MCP23017_ADDR, MCP23017_SPEED)
        self.mcu = self.i2c.get_mcu()
        self.report_time = MCP23017_REPORT_TIME
        self.data = 0
        self.gcode = self.printer.lookup_object('gcode')
        # Asing gcode_macro key_(key_name)_gcode: M117 Key (name) Press
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.KEYS_TMPL = {}
        for key in KEYS.iteritems():
            self.KEYS_TMPL[key[0]] = gcode_macro.load_template(config,
                'key_'+ key[0]+'_gcode', 'M117 Key '+key[0]+' Press')
        self.sample_timer = self.reactor.register_timer(self._sample_mcp23017)
        self.printer.add_object("mcp23017" + self.name, self)
        self.printer.register_event_handler("klippy:connect", self.handle_connect)
        # self.mcu.register_config_callback(self.build_config)
        # self.oid = self.i2c.get_oid()

    def handle_connect(self):
        self._init_mcp23017()
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return self.report_time

    def _init_mcp23017(self):

        try:
            # Port Directions
            self.write_register(IODIRA, 0x5f) # 0101 1111
            self.write_register(IODIRB, 0x6d) # 0110 1101
            # Keys PolUp
            self.write_register(GPPUA, 0x5f)
            self.write_register(GPPUB, 0x6d)
            # Keys Intterupts          
            self.write_register(IOCON, 0x40) # INT Mirror
            # self.write_register(IOCON, 0x42) # Mirror and PolUp INT pins
            self.write_register(INTCONA, 0x5f) # Compare mode
            self.write_register(INTCONB, 0x6d)
            self.write_register(DEFVALA, 0x5f) # FALLING mode
            self.write_register(DEFVALB, 0x6d)
            self.write_register(GPINTENA, 0x5f) # Enable
            self.write_register(GPINTENB, 0x6d)

            # gpio = self.read_gpio()
            # logging.info('mcp23017: Init GPIO %#x' % gpio)

            # for key in KEYS.iteritems():
            # logging.info('key_%s', key[0])

            # self.led_test()

        except Exception:
            logging.exception("mcp23017: Init Registers")


    def _sample_mcp23017(self, eventtime):
        try:
            ### Keys Hook (Non innterupt)
            key_int = self.read_int()
            # logging.info('mcp23017: INTF %#x' % intf)
            if key_int in KEYS.itervalues():
                key_name = self.get_key_name(KEYS, key_int)
                # if gpio == KEYS['1']:
                self.gcode.run_script(self.KEYS_TMPL[key_name].render())
                # self.data = key_name
                # logging.info('mcp23017: data %s' % self.data)

            # self.write_gpio(0x5f6d)
            # logging.info('mcp23017: INT %#x', self.read_int())
            # self.led_on(1)

        except Exception:
            logging.exception("mcp23017: Error reading data")
            return self.reactor.NEVER

        measured_time = self.reactor.monotonic()
        self._callback(self.mcu.estimated_print_time(measured_time), self.data)
        return measured_time + self.report_time

    def led_test(self):
        try:
            for pin in LED.values():
                # logging.info('mcp23017: Led %d', pin)
                self.set_led(pin, 1)
                self.reactor.pause(self.reactor.monotonic() + 3) # wait 3s
                self.set_led(pin, 0)
        except Exception:
            logging.exception("mcp23017: Error Led Test")

    def read_register(self, reg_name):
        params = self.i2c.i2c_read([reg_name], 8)
        return bytearray(params['response'])[0]

    def write_register(self, reg_name, data):
        self.i2c.i2c_write([reg_name, data])
    
    def read_gpio(self):
        # Default GPIOAB: 0x5f6d
        a = self.read_register(GPIOA)
        b = self.read_register(GPIOB)
        ab = (a << 8) | b      
        # logging.info('mcp23017: Read A %#x B %#x' % (a,b))
        # logging.info('mcp23017: GPIO %#x' % ab)
        return ab

    def set_led(self, pin, mode):
        ## shell metod
        cmd = str(100 + pin) + ' ' + str(mode)
        # logging.info('mcp23017: %s', cmd)
        os.popen('gpio -x mcp23017:100:0x20 write '+ cmd)
        # output = stream.read()
    
    def write_gpio(self, data):
        a = data >> 8
        b = data & 0xff

        # logging.info('mcp23017: GPIO %#x (%s)' % (data, bin(data)))   
        # logging.info('mcp23017: GPIO %#x (%s) %#x (%s)' % (a, bin(a), b, bin(b)))
        self.i2c.i2c_write([GPIOA, a])
        self.i2c.i2c_write([GPIOB,b])

    def read_int(self):
        a = self.read_register(INTFA)
        b = self.read_register(INTFB)
        return (a | b)
        # logging.info('mcp23017: INTFA %#x INFB %#x INF %#x' % (a, b, (a | b)))

    def get_key_name(self, d, v):
        return next(key for key, value in d.iteritems() if value == v)

    def get_status(self, eventtime):
        return {
            'data:': self.data,
        }

def load_config(config):
    return mcp23017(config)
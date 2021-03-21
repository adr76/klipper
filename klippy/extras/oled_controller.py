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

leds = { # name : [pin, state]
    'filament': 2, #blue
    'pwr'     : 13, #red
    'fan'     : 16, #blue
    'print'   : 6, #green
    'pause'   : 8 #yellow
}

# Buttons 
buttons = {
    'up' : 17, 'filament' : 20, 'down' : 24,
    '1' : 1, '2' : 2, '3' : 4, '4' : 8, '5' : 16,
    'pwr' : 48, 'fan' : 80, 'pause' : 64
}

MCP23017_REPORT_TIME = .5 #sec

# Klipper Log
# tail -f /tmp/klippy.log | grep -i -E "(mcp23017:|oled_controller.py|error|Unable)"
# tail -f /tmp/klippy.log | grep -i -E "(mcp23017:|error|Unable)

class mcp23017(object):
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.sample_timer = self.reactor.register_timer(self._sample_mcp23017)
        self.i2c = bus.MCU_I2C_from_config(config, MCP23017_ADDR, MCP23017_SPEED)
        self.mcu = self.i2c.get_mcu()
        self.report_time = MCP23017_REPORT_TIME
        self.last_btn = None
        self.led_state = dict.fromkeys(leds, 0)
        # logging.info('mcp23017: led_state %s' % self.led_state)
        # Init Gcode macros
        self.gcode = self.printer.lookup_object('gcode')
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.btn_tmpl = {}
        for key, val in buttons.items():
            tmpl = 'btn_'+key+'_gcode'
            gcode = 'M117 Key '+ key
            self.btn_tmpl[key] = gcode_macro.load_template(config, tmpl, gcode)
            # logging.info('mcp23017: %s | %s' % (key, gcode))
        self.printer.add_object("mcp23017" + self.name, self)
        self.printer.register_event_handler("klippy:connect", self.handle_connect)
        # self.printer.register_event_handler("klippy:ready ", self.handle_ready)
        # self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)
        # self.mcu.register_config_callback(self.build_config)

    def handle_connect(self):
        self._init_mcp23017()
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return self.report_time

    def _init_mcp23017(self):
        try: # Init Registers
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
            # self.led_test()
        except Exception:
            logging.exception("mcp23017: Error init registers")

    def _sample_mcp23017(self, eventtime):
        try:
            ### Button Press Hook
            btn_name = self.get_btn()
            if btn_name:
                # Set buttons led
                if btn_name in leds.keys():
                    if self.led_state[btn_name]:
                        state = 0
                    else:
                        state = 1
                    logging.info('mcp23017: set_state %s %d' % (btn_name, state))
                    self.set_led(btn_name, state)
                    self.led_state[btn_name] = state
                # Run button macros
                # self.gcode.run_script(self.btn_tmpl[btn_name].render())
                self.last_btn = btn_name
                # logging.info('mcp23017: data %s' % self.data)
        except Exception:
            logging.exception("mcp23017: Error reading data")
            return self.reactor.NEVER

        measured_time = self.reactor.monotonic()
        # self._callback(self.mcu.estimated_print_time(measured_time), self.data)
        # logging.info('mcp23017: %d' % measured_time)
        # self.data = measured_time
        return measured_time + self.report_time

    def led_test(self):
        try:
            for pin in leds.values():
                logging.info('mcp23017: led test %d', pin)
                self.set_led(pin, 1)
                self.reactor.pause(self.reactor.monotonic() + 3) # wait 3s
                self.set_led(pin, 0)
        except Exception:
            logging.exception("mcp23017: Error Led Test")

    def read_register(self, reg_name):
        params = self.i2c.i2c_read([reg_name], 8)
        return bytearray(params['response'])[0]

    def read_register_os(self, reg_name):
        stream = os.popen('i2cget -y 0 0x20 '+ str(reg_name))
        output = stream.read()
        stream.close()
        return output

    def write_register(self, reg_name, data):
        self.i2c.i2c_write([reg_name, data])
        # logging.info('mcp23017: write_register %#x %#x' % (reg_name, data))
    
    def read_gpio(self):
        # Default GPIOAB: 0x5f6d
        a = self.read_register(GPIOA)
        b = self.read_register(GPIOB)
        ab = (a << 8) | b      
        # logging.info('mcp23017: Read A %#x B %#x' % (a,b))
        # logging.info('mcp23017: GPIO %#x' % ab)
        return ab

    def set_led(self, led, on):
        a = self.read_register(OLATA)
        b = self.read_register(OLATB)
        gpio = (a << 8) | b
        n = leds[led]

        if on:
            new_gpio = gpio | (1<<n)
        else:
            new_gpio = gpio & ~(1<<n)
       
        logging.info('led:  %s %d %d' % (led, on, n))
        logging.info('old gpio:  %#x %s' % (gpio, bin(gpio)))
        logging.info('new gpio:  %#x %s' % (gpio, bin(new_gpio)))

        # self.write_gpio(new_gpio)

        ## shell metod
        # cmd = "gpio -x mcp23017:100:0x20 write "+ str(100 + pin) + " " + str(on)
        # logging.info('mcp23017: set_led %s', cmd)
        # subprocess.run(["gpio", "-x", "mcp23017:100:0x20", "write", str(100 + pin), str(on)])
        # stream = os.popen(cmd)
        # stream.close()
    
    def write_gpio(self, data):
        a = data >> 8
        b = data & 0xff

        # logging.info('mcp23017: GPIO %#x (%s)' % (data, bin(data)))   
        # logging.info('mcp23017: GPIO %#x (%s) %#x (%s)' % (a, bin(a), b, bin(b)))
        self.i2c.i2c_write([GPIOA, a])
        self.i2c.i2c_write([GPIOB,b])

    def get_btn(self):
        a = self.read_register(INTFA)
        b = self.read_register(INTFB)
        if (a or b):
            if b: b = b + 16
            val = a+b
            # logging.info('btnval: %d' % val)
            if val in buttons.itervalues():
                return self.get_dict_key(buttons, val)
            else:
                return None    
        else:
            return None

    def get_dict_key(self, _dict, _val):
        # return next(key for key, value in _dict.items() if value == _val)
        for k, v in _dict.items():
            if v == _val:
                # logging.info('dict_key:  %s | %s' % (v, k))
                return k

    def get_status(self, eventtime):
        return {
            'key:': self.last_btn,
            'leds' : self.led_state,
        }

def load_config(config):
    return mcp23017(config)
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
IOCON      = 0x0A
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

DEFA = 0x5f
DEFB = 0x6d
DEFAB = 0x6d5f

#       LED1 LED2 LED3 LED4 LED5
# PORT  9    12   15   5    7  
#       KEY1 KEY2 KEY3 KEY4 KEY5 KEY6 KEY7 KEY8 KEY9 KEY10 KEY11
# PORT   8    10   11   0    1    2    3    4    13   14    6
#
# PA|PB   1111 1010 | 1011 0110
# PA = int('0b01011111', 2) # 0x5f
# PB = int('0b01101101', 2) # 0x6d

leds = {
    'filament': 9, #blue
    'pwr'     : 12, #red
    'fan'     : 15, #blue
    'pause'   : 5, #green
    'print'   : 7 #yellow
}

# Buttons 
buttons = {
    'up' : 0x100,
    'filament' : 0x400,
    'down' : 0x800,
    '1' : 0x1,
    '2' : 0x2, '3' : 0x4, '4' : 0x8, '5' : 0x10,
    'pwr' : 0x2000, 'fan' : 0x4000, 'pause' : 0x40
    # 'fan_pwr' : 0x6000
}

MCP23017_REPORT_TIME = 0.5 #sec
LONG_PRESS = 3 #counts

# Klipper Log
# tail -f /tmp/klippy.log | grep -i -E "(mcp23017:|error|Unable)
# tail -f /tmp/klippy.log | grep -v Stats

class mcp23017(object):
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.sample_timer = self.reactor.register_timer(self._sample_mcp23017)
        self.i2c = bus.MCU_I2C_from_config(config, MCP23017_ADDR, MCP23017_SPEED)
        self.mcu = self.i2c.get_mcu()
        self.report_time = MCP23017_REPORT_TIME
        self.last_button = None
        self.button_event = {'button': None, 'event':None}
        self.pressed_button = None
        self.repeat_count = 0
        self.led_state = dict.fromkeys(leds, 0)
        # Init Gcode macros
        self.gcode = self.printer.lookup_object('gcode')
        gcode_macro = self.printer.load_object(config, 'gcode_macro')
        self.ready_gcode = gcode_macro.load_template(config, 'ready_gcode','M117 Ready')
        self.disconnect_gcode = gcode_macro.load_template(config, 'disconnect_gcode','M117 Disconnect')
        self.btn_tmpl = {}
        for key, val in buttons.items():
            tmpl = 'btn_'+key+'_gcode'
            gcode = 'M117 '+key
            self.btn_tmpl[key] = gcode_macro.load_template(config, tmpl, gcode)
        #
        self.printer.add_object(self.name, self)
        self.printer.register_event_handler("klippy:connect", self.handle_connect)
        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)
        # self.mcu.register_config_callback(self.build_config)

    def handle_connect(self):
        self._init_mcp23017()
        # self.led_test()
        # self.set_led('pwr', 1)
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def handle_ready(self):
        self.gcode.run_script(self.ready_gcode.render())

    def handle_disconnect(self):
        self.gcode.run_script(self.disconnect_gcode.render())

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return self.report_time

    def _init_mcp23017(self):
        try: # Init Registers
            # Port Directions
            self.write_register(IODIRA, 0x5f) # ~1111 1010
            self.write_register(IODIRB, 0x6d) # ~1011 0110
            # Leds Off
            self.write_register(GPIOA, 0x5f)
            self.write_register(GPIOB, 0x6d)
            # Keys PolUp
            self.write_register(GPPUA, 0x5f)
            self.write_register(GPPUB, 0x6d)
            # Disable Intterupts
            # self.write_register(GPINTENA, 0x00) # Disable INTA
            # self.write_register(GPINTENB, 0x00) # Disable INTB        
            # Enable Intterupts
            self.write_register(IOCON, 0x40) # INT Mirror
            # self.write_register(IOCON, 0x42) # Mirror and PolUp INT pins
            self.write_register(INTCONA, 0x5f) # Compare mode
            self.write_register(INTCONB, 0x6d)
            self.write_register(DEFVALA, 0x5f) # FALLING mode
            self.write_register(DEFVALB, 0x6d)
            self.write_register(GPINTENA, 0x5f) # Enable
            self.write_register(GPINTENB, 0x6d)
        except Exception:
            logging.exception("mcp23017: Error init registers")

    def _sample_mcp23017(self, eventtime):
        try:
            ### Button Events Hook
            self._button_event()
            event = self.button_event['event']
            button = self.button_event['button']
            # logging.info('%s : %s' % (button, event))
            if event == 'release':
                # logging.info('Button %s: Release' % button)
                self.last_button = button
                if button in leds.keys(): self.change_led(button)
                self.gcode.run_script(self.btn_tmpl[button].render())
            # if event == 'lpress':
                # logging.info('Button %s: Long Press' % button)

        except Exception:
            logging.exception("mcp23017: Error reading data")
            return self.reactor.NEVER

        measured_time = self.reactor.monotonic()
        # self._callback(self.mcu.estimated_print_time(measured_time), self.data)
        # logging.info('mcp23017: %d' % measured_time)
        return measured_time + self.report_time

    def _button_event(self):
        event = None
        button = None
        # Get MCP Button by Interrupt Change
        a = self.read_register(INTFA)
        b = self.read_register(INTFB)
        data = (b << 8) | a
        # logging.info('data: %s %s' % (format(data, '016b'), hex(data)))
        if data in buttons.itervalues():
            btn_name = self.get_dict_key(buttons, data)
            button   = btn_name
            if self.pressed_button:
                self.repeat_count += 1
                # Repeat Event
                event = 'repeat'
                # Long Press Event
                if self.repeat_count > LONG_PRESS:
                    event = 'lpress'
                    self.repeat_count = 0
            else:
                # Press Event
                event = 'press'
            self.pressed_button = btn_name
        elif self.pressed_button:
            # Relese Event
            button = self.pressed_button
            event  = 'release'
            self.repeat_count = 0
            self.pressed_button = None

        self.button_event.update({'button': button, 'event':event})

    def set_led(self, led, state):
        # Set LED state On/Off
        bit = leds[led]       
        if bit < 8:
            self.bit_set(GPIOA, bit, state)
        else:
            self.bit_set(GPIOB, bit-8, state)

        self.led_state[led] = state
        # logging.info('Set Led: %s | %d' % (led, state))

    def change_led(self, led):
        on = self.led_state[led]
        if on:
            self.set_led(led, 0)
        else:       
            self.set_led(led, 1)

    def led_test(self):
        try:
            for led in leds.keys():
                logging.info('Led test: %d', led)
                self.set_led(led, 1)
                self.reactor.pause(self.reactor.monotonic() + 1) # wait
                self.set_led(led, 0)
        except Exception:
            logging.exception("mcp23017: Error Led Test")

    def bit_set(self, reg, bit, val):
        reg_data = self.read_register(reg)
        if val:
            reg_data |= (1 << bit)
        else:
           reg_data &= ~(1 << bit)
           
        self.write_register(reg, reg_data)
 
    def bit_change(self, reg, bit):
        reg_data = self.read_register(reg)
        reg_data ^= (1 << bit) 
        self.write_register(reg, reg_data)  
           
    def read_register(self, reg_name):
        params = self.i2c.i2c_read([reg_name], 8)
        # response = ['response': '\x00\x00\x00_m_m_']
        # logging.info('%s' % params['response'])
        return bytearray(params['response'])[0]

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
            
    def write_gpio(self, data):
        a = data >> 8
        b = data & 0xff
        # logging.info('mcp23017: GPIO %#x (%s)' % (data, bin(data)))   
        # logging.info('mcp23017: GPIO %#x (%s) %#x (%s)' % (a, bin(a), b, bin(b)))
        self.i2c.i2c_write([GPIOA, a])
        self.i2c.i2c_write([GPIOB, b])

    def get_dict_key(self, _dict, _val):
        # return next(key for key, value in _dict.items() if value == _val)
        for k, v in _dict.items():
            if v == _val:
                # logging.info('dict_key:  %s | %s' % (v, k))
                return k

    def get_status(self, eventtime):
        return {
            'last_button:': self.last_button,
            'buton': self.button_event['button'],
            'event': self.button_event['event'],
            'repeat': self.repeat_count,
            'leds' : self.led_state,
        }

def load_config(config):
    return mcp23017(config)
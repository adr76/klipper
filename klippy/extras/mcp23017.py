# MCP23017 Extra
#
# Copyright (C) 2018  Florian Heilmann <Florian.Heilmann@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os
import logging
import pins
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

# GPIOA_DEF = 0x5f
# GPIOB_DEF = 0x6d
# GPIO_DEF = 0x5f6d

# Byte registers
REG_I_ON = [0x2A, 0x2D, 0x30, 0x33, 0x36, 0x3B, 0x40, 0x45,
            0x4A, 0x4D, 0x50, 0x53, 0x56, 0x5B, 0x5F, 0x65]

class MCP23017(object):
    def __init__(self, config):
        self._printer = config.get_printer()
        self._name = config.get_name().split()[1]
        self._i2c = bus.MCU_I2C_from_config(config, default_speed=400000)
        self._ppins = self._printer.lookup_object("pins")
        self._ppins.register_chip("mcp23017" + self._name, self)
        self._mcu = self._i2c.get_mcu()
        self._mcu.register_config_callback(self._build_config)
        self._oid = self._i2c.get_oid()
        # Set up registers default values
        self.reg_dict = {REG_DIR : 0xFFFF, REG_DATA : 0,
                         REG_PULLUP : 0, REG_PULLDOWN : 0,
                         REG_INPUT_DISABLE : 0, REG_ANALOG_DRIVER_ENABLE : 0}
        # self.reg_i_on_dict = {reg : 0 for reg in REG_I_ON}
    def _build_config(self):
        # self._mcu.add_config_cmd("i2c_write oid=%d data=%02x%02x" % (
        #     self._oid, REG_RESET, 0x12))
        # Init Registers
        # for _reg, _data in self.reg_dict.items():
            logging.info('mcp23017: InitRegs %#x %#x', % (self._reg, _data))
            # self._mcu.add_config_cmd("i2c_write oid=%d data=%02x%04x" % (
            #     self._oid, _reg, _data), is_init=True)
    def setup_pin(self, pin_type, pin_params):
        if pin_type == 'digital_out' and pin_params['pin'][0:4] == "PIN_":
            return MCP23017_digital_out(self, pin_params)
        raise pins.error("Wrong pin or incompatible type: %s with type %s! " % (
            pin_params['pin'][0:4], pin_type))
    def get_mcu(self):
        return self._mcu
    def get_oid(self):
        return self._oid
    def clear_bits_in_register(self, reg, bitmask):
        if reg in self.reg_dict:
            self.reg_dict[reg] &= ~(bitmask)
        elif reg in self.reg_i_on_dict:
            self.reg_i_on_dict[reg] &= ~(bitmask)
    def set_bits_in_register(self, reg, bitmask):
        if reg in self.reg_dict:
            self.reg_dict[reg] |= bitmask
        elif reg in self.reg_i_on_dict:
            self.reg_i_on_dict[reg] |= bitmask
    def set_register(self, reg, value):
        if reg in self.reg_dict:
            self.reg_dict[reg] = value
        elif reg in self.reg_i_on_dict:
            self.reg_i_on_dict[reg] = value
    def send_register(self, reg, print_time):
        data = [reg & 0xFF]
        if reg in self.reg_dict:
            # Word
            data += [(self.reg_dict[reg] >> 8) & 0xFF,
                     self.reg_dict[reg] & 0xFF]
        elif reg in self.reg_i_on_dict:
            # Byte
            data += [self.reg_i_on_dict[reg] & 0xFF]
        clock = self._mcu.print_time_to_clock(print_time)
        self._i2c.i2c_write(data, minclock=self._last_clock, reqclock=clock)

class MCP23017_digital_out(object):
    def __init__(self, MCP23017, pin_params):
        self._mcp23017 = MCP23017
        self._mcu = MCP23017.get_mcu()
        self._mcp_pin = int(pin_params['pin'].split('_')[1])
        self._bitmask = 1 << self._mcp_pin
        self._pin = pin_params['pin']
        self._invert = pin_params['invert']
        self._mcu.register_config_callback(self._build_config)
        self._start_value = self._shutdown_value = self._invert
        self._is_static = False
        self._max_duration = 2.
        self._set_cmd = self._clear_cmd = None
        # Set direction to output
        self._mcp23017.clear_bits_in_register(REG_DIR, self._bitmask)
    def _build_config(self):
        if self._max_duration:
            raise pins.error("MCP23017 pins are not suitable for heaters")
    def get_mcu(self):
        return self._mcu
    def setup_max_duration(self, max_duration):
        self._max_duration = max_duration
    def setup_start_value(self, start_value, shutdown_value, is_static=False):
        if is_static and start_value != shutdown_value:
            raise pins.error("Static pin can not have shutdown value")
        self._start_value = (not not start_value) ^ self._invert
        self._shutdown_value = self._invert
        self._is_static = is_static
        # We need to set the start value here so the register is
        # updated before the MCP23017 class writes it.
        if self._start_value:
            self._mcp23017.set_bits_in_register(REG_DATA, self._bitmask)
        else:
            self._mcp23017.clear_bits_in_register(REG_DATA, self._bitmask)
    def set_digital(self, print_time, value):
        if int(value) ^ self._invert:
            self._mcp23017.set_bits_in_register(REG_DATA, self._bitmask)
        else:
            self._mcp23017.clear_bits_in_register(REG_DATA, self._bitmask)
        self._mcp23017.send_register(REG_DATA, print_time)
    def set_pwm(self, print_time, value, cycle_time=None):
        self.set_digital(print_time, value >= 0.5)

def load_config_prefix(config):
    return MCP23017(config)

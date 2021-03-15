# Oled Controller Module Extra
# OLED 1.3"  I2C SH1106
# MCP23013 - 11 Keys, 5 Leds
# 
# Copyright (C) 2021  adr76 <Oleksandr.druz@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

# import pins
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

REG_DATA = {
    'DEFA':int('01011111',2),
    'DEFB':int('01101101',2),
    'LED1':int('01101111',2), #PB
    'LED2':int('01111101',2), #PB
    'LED3':int('11101101',2), #PB
    'LED4':int('01111111',2), #PA
    'LED5':int('11011111',2), #PA
    'LED45':int('11111111',2), #PA
}

LED = {
    '1'     : [0x13, 0x6f], #blue
    '2'     : [0x13, 0x7d], #red
    '3'     : [0x13, 0xed], #blue
    '4'     : [0x12, 0x7f], #green
    '5'     : [0x12, 0xdf], #yellow
    '45'    : [0x12, 0xff], #green & yellow
    'OFFA'  : [0x12, 0x5f], # Off 4 5
    'OFFB'  : [0x13, 0x6d]  # Off 1 2 3
}

MCP23017_REPORT_TIME = .8

class mcp23017(object):
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.i2c = bus.MCU_I2C_from_config(config, MCP23017_ADDR, MCP23017_SPEED)
        self.mcu = self.i2c.get_mcu()
        self.report_time = MCP23017_REPORT_TIME
        self.data = "null"
        self.sample_timer = self.reactor.register_timer(self._sample_mcp23017)
        self.printer.add_object(self.name, self)
        # self.printer.register_event_handler("klippy:ready", self.handle_connect)
        self.printer.register_event_handler("klippy:connect", self.handle_connect)
        # self.mcu.register_config_callback(self.build_config)
        # self.oid = self.i2c.get_oid()

    def handle_connect(self):
        self._init_mcp23017()
        # self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return self.report_time

    def _init_mcp23017(self):
        logging.info("mcp23017: Init")
       
        try: # Init Registers
            # Port Directions
            self.write_register(IODIRA, 0x5f)
            self.write_register(IODIRB, 0x6d)
            # Keys PolUp
            self.write_register(GPPUA, 0x5f)
            self.write_register(GPPUB, 0x6d)
            # Keys Intterupts
            # self.write_register(IOCON, 0x40) # INT Mirror
            # self.write_register(IOCON, 0x42) # INT Mirror and PolUp
            # self.write_register(GPINTENA, 0x5f)
            # self.write_register(GPINTENB, 0x6d)

            a = self.read_register(GPIOA)
            b = self.read_register(GPIOB)
            logging.info('mcp23017: GPIOA %#x GPIOB %#x' % (a,b))
                    
        except Exception:
            logging.exception("mcp23017: Init Registers")
        
        try: # Led test
            self.write_register(GPIOA, 0xff)
            self.write_register(GPIOB, 0xff)
            self.reactor.pause(self.reactor.monotonic() + 3) # wait 3s
            self.write_register(GPIOA, 0x5f)
            self.write_register(GPIOB, 0x6d)
        except Exception:
            logging.exception("mcp23017: Error Led Test")

        # Wait 15ms after reset
        # self.reactor.pause(self.reactor.monotonic() + .15)

    def _sample_mcp23017(self, eventtime):
        try:
            a = self.read_register(GPIOA)
            b = self.read_register(GPIOB)
            logging.info('mcp23017: GPIOA %#x GPIOB %#x' % (a,b))
        except Exception:
            logging.exception("mcp23017: Error reading data")
            return self.reactor.NEVER

        measured_time = self.reactor.monotonic()
        # self._callback(self.mcu.estimated_print_time(measured_time), self.data)
        return measured_time + self.report_time

    def read_register(self, reg_name):
        # read register
        # regs = [MCP23017_REGS[reg_name]]
        params = self.i2c.i2c_read([reg_name], 8)
        return bytearray(params['response'])[0]

#    def read_GPIOAB(self):
#         a = self.read_register(GPIOA)
#         b = self.read_register(GPIOB)
#         logging.info('mcp23017: GPIOA %#x GPIOB %#x' % (a,b))

    def write_register(self, reg_name, data):
        # self.i2c.i2c_write([0x13, 0x6f])
        # if type(data) is not list:
        #     data = [data]
        # reg = MCP23017_REGS[reg_name]
        # data.insert(0, reg)
        # logging.info('mcp23017: data %#x' % data[0])
        self.i2c.i2c_write([reg_name, data])

    def get_status(self, eventtime):
        return {
            'data': self.data,
        }

def load_config(config):
    return mcp23017(config)
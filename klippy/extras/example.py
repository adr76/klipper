# Support for I2C based EXAMPLE/EXAMPLEA status sensors
#
# Copyright (C) 2020  Boleslaw Ciesielski <combolek@users.noreply.github.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
# from . import bus

EXAMPLE_REPORT_TIME = 0.5
# EXAMPLE_MIN_REPORT_TIME = .5

class EXAMPLE:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.report_time = config.getfloat('example_report_time', EXAMPLE_REPORT_TIME)
        self.status = 'not redy'
        self.sample_timer = self.reactor.register_timer(self._sample_example)
        self.printer.add_object("example " + self.name, self)
        self.printer.register_event_handler("klippy:connect",
                                            self.handle_connect)

    def handle_connect(self):
        self._init_example()
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_callback(self, cb):
        self._callback = cb

    def get_report_time_delta(self):
        return self.report_time

    def _init_example(self):
            self.status = 'redy'
            logging.info("example: Status %s" % self.status)

    def _sample_example(self, eventtime):
        try:
            self.status = 'sample'
        except Exception:
            logging.exception("example: Error sample")
            self.status = 'error'
            return self.reactor.NEVER

        measured_time = self.reactor.monotonic()
        self._callback(self.mcu.estimated_print_time(measured_time), self.status)
        return measured_time + self.report_time

    def get_status(self, eventtime):
        return {
            'status': self.status,
        }


def load_config(config):
    return EXAMPLE(config)
    # Register sensor
    # pheaters = config.get_printer().load_object(config, "heaters")
    # pheaters.add_sensor_factory("EXAMPLE", EXAMPLE)
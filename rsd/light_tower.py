#!/usr/bin/python3

import time
import threading
from rsd.packml.packml import PackMLState as S, STATES
from rsd.utils.rsd_redis import RsdRedis

GREEN, YELLOW, RED = "GREEN", "YELLOW", "RED"
COLORS = (GREEN, YELLOW, RED)

OFF, SOLID, FLASH = "OFF", "SOLID", "FLASH"

# colors not defined default to OFF
light_config = {
    S.ABORTING: {RED: FLASH},
    S.ABORTED: {RED: FLASH},
    S.CLEARING: {RED: FLASH},
    S.STOPPING: {RED: SOLID},
    S.STOPPED: {RED: SOLID},
    S.RESETTING: {YELLOW: FLASH},
    S.IDLE: {GREEN: FLASH},
    S.STARTING: {GREEN: SOLID},
    S.EXECUTE: {GREEN: SOLID},
    S.HOLDING: {YELLOW: FLASH, GREEN: FLASH},
    S.HELD: {YELLOW: FLASH, GREEN: FLASH},
    S.UNHOLDING: {GREEN: SOLID},
    S.SUSPENDING: {YELLOW: SOLID},
    S.SUSPENDED: {YELLOW: SOLID},
    S.UNSUSPENDING: {GREEN: SOLID},
}


class LightTower:
    odd = False

    def __init__(self, debug=False):
        super().__init__()
        self.should_stop = False
        self.debug = debug
        self.r = RsdRedis()
        self.state = self.r.get("state")
        if self.state is None:
            self.state = S.ABORTED
        self.t = None

    def set_state(self, data):
        old_state, new_state = data
        self.state = new_state
        print("STATE:", STATES[new_state])

    def start(self, blocking=True):
        assert self.t is None
        sub = self.r.subscribe("state_changed", self.set_state)

        def loop():
            while not self.should_stop:
                self.set_lights()
                time.sleep(.5)
            self.r.unsubscribe(sub)

        self.t = threading.Thread(target=loop)
        self.t.start()
        if blocking:
            self.t.join()
        return self

    def set_lights(self):
        state = self.state
        if state is None:
            state = S.STOPPED
        l_conf = light_config[state]
        condition = (SOLID, FLASH) if self.odd else (SOLID,)
        lights_on = [l_conf.get(color, OFF) in condition for color in COLORS]
        self.odd = not self.odd

        if self.debug:
            print(STATES[state], "ODD" if self.odd else "EVEN", lights_on)
        else:
            for output_id, light_on in enumerate(lights_on):
                self.r.publish("setStandardDigitalOut", (output_id, light_on))

    def stop(self):
        self.should_stop = True
        self.t.join()

    def __del__(self):
        self.stop()


def main():
    lt = LightTower()
    lt.start()


def _test():
    lt = LightTower(debug=True)
    lt.start(blocking=False)

    r = RsdRedis()
    for state in light_config.keys():
        time.sleep(3)
        r.publish("state_changed", (None, state))

    lt.stop()


if __name__ == '__main__':
    TEST = False
    if TEST:
        _test()
    else:
        main()

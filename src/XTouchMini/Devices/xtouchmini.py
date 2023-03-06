# Deck controller for Behringer X-Touch Mini devices
#
import time
import logging
import threading
import random
import mido
from enum import Enum

logger = logging.getLogger("XTouchMini")
logger.setLevel(logging.DEBUG)

GLOBAL_CHANNEL = 0
CHANNEL = 10

class LED_MODE(Enum):
    SINGLE = 0
    TRIM = 1
    FAN = 2
    SPREAD = 3

MAKIE_MAPPING = {
    0: 89,
    1: 90,
    2: 40,
    3: 41,
    4: 42,
    5: 43,
    6: 44,
    7: 45,
    8: 87,
    9: 88,
   10: 91,
   11: 92,
   12: 86,
   13: 93,
   14: 94,
   15: 95,
  "A": 84,
  "B": 85
}

class XTouchMini:

    def __init__(self, input_device_name: str, output_device_name: str):
        self.name = input_device_name   # label
        self.input_device_name = input_device_name
        self.output_device_name = output_device_name

        self._input_device = None
        self._output_device = mido.open_output(output_device_name)

        self.callback = None
        self.timeout = 10
        self.makie = False

        self.running = False
        self.thread = None

    def id(self):
        return self.name

    def deck_type(self):
        return "xtouchmini"

    def open(self):
        pass

    def close(self):
        pass

    def reset(self, silence: bool = True):
        if silence:
            l= logger.getEffectiveLevel()
            logger.setLevel(logging.WARNING)
        logger.debug(f"reset: reseting..")
        for i in MAKIE_MAPPING.keys():
            self.set_key(i)
        for i in range(8):
            self.set_control(i, value=0)
        logger.debug(f"reset: ..reset")
        if silence:
            logger.setLevel(l)

    def is_visual(self):
        return False

    def get_serial_number(self):
        return self.input_device_name

    def key_names(self):
        a = [i for i in range(16)]
        for i in range(1, 9):
            a.append(f"Knob{i}")
        return a

    def set_callback(self, callback: callable):
        self.callback = callback


    def _read_makie(self, msg: mido.Message) -> None:
        # ** MAKIE VERSION **
        # logger.debug(f"_read_makie: {msg}")
        payload = None
        if msg.type == "note_on":
            payload = { "key": msg.note, "state": 1 if msg.velocity == 127 else 0 }
        elif msg.type == "note_off":
            payload = { "key": msg.note, "state": 0 }
        elif msg.type == "control_change":
            if msg.control in [9, 10]:  # slider A and B
                payload = { "key": msg.control, "state": msg.value }
            else:
                payload = { "key": msg.control, "state": 2 if msg.value > 64 else 3 }
        elif msg.type == "pitchwheel":
                payload = { "key": msg.channel, "state": msg.pitch }

        if self.callback is not None and payload is not None:
            payload["deck"] = self
            self.callback(**payload)


    def _read(self, msg: mido.Message) -> None:
        # ** STANDARD VERSION **
        #logger.debug(f"_read: {msg}")
        payload = None
        if msg.type == "note_on":
            payload = { "key": msg.note, "state": 1 }
        elif msg.type == "note_off":
            payload = { "key": msg.note, "state": 0 }
        elif msg.type == "control_change":
            if msg.control in [9, 10]:  # slider A and B
                payload = { "key": msg.control, "state": msg.value }
            else:
                payload = { "key": msg.control, "state": 2 if msg.value > 64 else 3 }

        if self.callback is not None and payload is not None:
            payload["deck"] = self
            self.callback(**payload)


    def _write(self, message: mido.Message) -> None:
        if self._output_device is not None:
            logger.debug(f"_write: sending '{str(message)}'")
            self._output_device.send(message)


    def send(self, message: mido.Message):
        self._write(message)
        # logger.debug(f"send: sent: {message}")

    def set_makie(self, on:int = 1):
        logger.debug(f"start: setting Makie mode {on}..")
        m = mido.Message(type="control_change", control=127, value=on)
        self.send(m)
        self.makie = on != 0

    def start(self) -> None:
        if not self.running:
            logger.debug(f"start: starting {self.name}..")

            self.set_makie()
            time.sleep(1)
            logger.debug(f"start: ..makie set")

            self.running = True
            self.thread = threading.Thread(target=self.loop)
            self.thread.name = "XTouchMini::loop"
            self.thread.start()
            logger.debug(f"start: ..started")
        else:
            logger.debug(f"start: already running")

    def loop(self) -> None:
        m = None
        try:
            logger.debug(f'start: opening MIDI device: "{self.name}"..')
            m = mido.open_input(self.name, callback=self._read_makie if self.makie else self._read)
            logger.debug('start: ..device opened')
            while self.running:
                time.sleep(self.timeout)
        except Exception as e:
            if m is not None and not m.closed:
                m.close()
            logger.error(f"loop: exception:", exc_info=1)
        except KeyboardInterrupt:
            if m is not None and not m.closed:
                m.close()
                logger.debug(f'loop: closed MIDI device: "{self.name}"')
            logger.debug(f'loop: KeyboardInterrupt: "{self.name}"')
        logger.error(f"loop: {self.name}: exited")

    def stop(self) -> None:
        if self.running:
            logger.debug(f"stop: stopping {self.name} (wait can last up to {2 * self.timeout}s)..")
            self.running = False
            if not self.thread.join(2 * self.timeout):
                logger.warning(f"stop: did not stop cleanly")
            self.thread = None

            self.set_makie(0)
            logger.debug(f"stop: ..makie unset")

            if self._output_device is not None and not self._output_device.closed:
                self._output_device.close()
            logger.debug(f"stop: ..stopped")
        else:
            logger.debug(f"stop: not running")


    # ##########################################
    # User Interface
    #
    def set_brightness(self, brightness: int):
        pass

    def set_key(self, key: int, on:bool=False, blink:bool=False):
        # https://stackoverflow.com/questions/39435550/changing-leds-on-x-touch-mini-mackie-control-mc-mode
        # To blink, key must be on=True and blink=True
        if key not in MAKIE_MAPPING.keys():
            logger.warning(f"set_key: invalid key {key}")
            return
        velocity = 0
        if on:
            velocity = 127
            if blink:
                velocity = 1
        m = mido.Message(type="note_on", note=MAKIE_MAPPING[key], velocity=velocity)
        self.send(m)

    # #: Modes : There are 11 LEDs: 0-4, middle=5, 6-10
    # 0: Single: 00000001000
    # 1: Fan   : 00000111000
    # 2: Trim  : 11111111000
    # 3: Spread: 00111111100
    #
    def set_control(self, key: int, value:int, mode: LED_MODE = LED_MODE.SINGLE):
        if key < 0 or key > 7:
            logger.warning(f"set_control: invalid key {key}")
            return
        if value < 0:
            logger.warning(f"set_control: invalid value {value}, setting min")
            value = 0
        elif value > 11:
            logger.warning(f"set_control: invalid value {value}, setting max")
            value = 11
        m = mido.Message(type="control_change", control=48+key, value=(mode.value * 16)+value)
        self.send(m)


    def test(self):
        m = mido.Message(type="control_change", control=127, value=1)
        self.send(m)
        time.sleep(1)
        value_offset = 8
        mode = None

        logger.debug(f"test: testing..")
        self.set_makie()

        logger.debug(f"test: ..set..")
        for i in MAKIE_MAPPING.keys():
            self.set_key(i, on=True)
            time.sleep(0.2)

        logger.debug(f"test: ..control..")
        for j in range(11):
            self.set_control(0, value=j, mode=LED_MODE.SINGLE)
            self.set_control(1, value=j, mode=LED_MODE.TRIM)
            self.set_control(2, value=j, mode=LED_MODE.FAN)
            self.set_control(3, value=j, mode=LED_MODE.SPREAD)
            self.set_control(4+0, value=j, mode=LED_MODE.SINGLE)
            self.set_control(4+1, value=j, mode=LED_MODE.TRIM)
            self.set_control(4+2, value=j, mode=LED_MODE.FAN)
            self.set_control(4+3, value=j, mode=LED_MODE.SPREAD)
            time.sleep(0.2)

        logger.debug(f"test: ..blink..")
        for i in MAKIE_MAPPING.keys():
            self.set_key(i, on=True, blink=True)

        n = 2
        logger.debug(f"test: ..reset in {n} seconds..")
        time.sleep(n)
        self.reset()

        self.set_makie(0)

        logger.debug(f"test: ..done")

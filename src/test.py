import time
import logging

from XTouchMini import DeviceManager

logging.basicConfig(level=logging.DEBUG)

devices = DeviceManager().enumerate()

def callback(msg):
    print(f">> {msg}")

if len(devices) > 0:
    l = devices[0]
    l.set_callback(callback)
    l.test()

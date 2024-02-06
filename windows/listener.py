"""
Listeners for aggregated keyboard and mouse events.

This is used for AFK detection on Linux, as well as used in aw-watcher-input to track input activity in general.

NOTE: Logging usage should be commented out before committed, for performance reasons.
"""

import logging
import threading
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import Dict, Any
import re




logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

def check_format(string):
    pattern = r"\\x[0-9a-fA-F]{2}"
    match = re.match(pattern, string)
    if match:
        return True
    else:
        return False

class EventFactory(metaclass=ABCMeta):
    def __init__(self) -> None:
        self.new_event = threading.Event()
        self._reset_data()

    @abstractmethod
    def _reset_data(self) -> None:
        self.event_data: Dict[list, int] = {}

    def next_event(self) -> dict:
        """Returns an event and prepares the internal state so that it can start to build a new event"""
        self.new_event.clear()
        data = self.event_data
        # self.logger.debug(f"Event: {data}")
        self._reset_data()
        return data
    def has_new_event(self) -> bool:
        return self.new_event.is_set()


class KeyboardListener(EventFactory):
    def __init__(self):
        EventFactory.__init__(self)
        self.logger = logger.getChild("keyboard")
        self.shift_flag = False
        self.alt_flag = False
        self.ctrl_flag = False

    def start(self):
        from pynput import keyboard

        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()


    def stop(self):
        self.listener.join()

    def _reset_data(self):
        self.event_data = {
            "data": [],
            'count': 0
            }
        

    def correct_ctrl_key_data(self, item):
        if self.event_data['data']:
            self.event_data['data'].pop()
        return '<ctrl + {}>'.format(item)
    
    def correct_shift_key_data(self, item):
        if self.event_data['data']:
            self.event_data['data'].pop()
        return '<shift + {}>'.format(item)
    
    def correct_alt_key_data(self, item):
        if self.event_data['data']:
            self.event_data['data'].pop()
        return '<alt + {}>'.format(item)
    
    def on_press(self, key):
        self.event_data['count'] += 1
        self.logger.debug(f"Press: {key}")
        print(f"Press: {key}")
        str_key = ""
        if hasattr(key, 'char'):
            # if ord(key.char) >= 0 and ord(key.char) <= 31:
            if self.ctrl_flag:
                str_key = chr(ord(key.char) + 64)
                str_key = self.correct_ctrl_key_data(str_key)
            elif self.shift_flag:
                str_key = self.correct_shift_key_data(key.char)
            elif self.alt_flag:
                str_key = self.correct_alt_key_data(key.char)
            elif str(key) == '<21>':
                
                self.alt_flag = True
                str_key = '<alt>'
            elif str(key) == '<25>':
                self.ctrl_flag = True
                str_key = '<ctrl>'

            else:
                str_key = key.char if key.char is not None else ""
        elif hasattr(key, 'name'):
            if key.name == "space":
                str_key = " "
            else:
                
                str_key = key.name
                if key.name == 'shift' or key.name == 'shift_r':
                    self.shift_flag = True
                    str_key = 'shift'
                elif key.name == 'alt_l' or key.name == 'alt_gr':
                    
                    self.alt_flag = True
                    str_key = 'alt'
                elif key.name == 'ctrl_l' or key.name == 'ctrl_r':
                    self.ctrl_flag = True
                    str_key = 'ctrl'

                str_key = "<{}>".format(str_key)

        if str_key:
            self.event_data['data'].append(str_key)
            self.new_event.set()

    def on_release(self, key):
        # Don't count releases, only clicks
        # self.logger.debug(f"Release: {key}")
        self.shift_flag = False
        self.alt_flag = False
        self.ctrl_flag = False
        pass


class MouseListener(EventFactory):
    def __init__(self):
        EventFactory.__init__(self)
        self.logger = logger.getChild("mouse")
        self.pos = None

    def _reset_data(self):
        self.event_data = {
            "data": [],
            'count': 0
            }

    def start(self):
        from pynput import mouse

        self.listener = mouse.Listener(
            on_click=self.on_click
        )
        self.listener.start()

    def stop(self):

        self.listener.join()


    def on_click(self, x, y, button, down):
        # self.logger.debug(f"Click: {button} at {(x, y)}")
        # Only count presses, not releases
        if down:
            self.event_data['count'] += 1
            self.new_event.set()



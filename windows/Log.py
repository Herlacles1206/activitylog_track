
from time import sleep
from datetime import datetime, timezone
import pytz

from listener import KeyboardListener, MouseListener

import os

import threading
import sys

import base64
import requests

import subprocess

from typing import Optional
import win32api
import win32gui
import win32process

import socketio

import pyscreeze

from io import BytesIO
import json
import atexit
import configparser

# Define a flag or event to signal the thread to exit
exit_flag = threading.Event()

local_url = 'localhost'
server_url = '144.126.254.71'

set_log_url = f'http://{server_url}:5000/api/activitylog/setlog'
authenticaion_url = f'http://{server_url}:5000/api/users/login_2'
socket_url = f'http://{server_url}:5000/api'
user_id = ''
recording_flag = False


sio = socketio.Client()

@sio.event
def connect():
    print('connection established')

@sio.on('captureFlag', namespace='/api')
def on_captureFlag(data):
    global recording_flag, user_id

    data_dict = json.loads(data)
    userid = data_dict.get('userid')
    flag = data_dict.get('flag')
    
    # print('message received')
    print('message received with ', data)
    if user_id == userid:
          recording_flag = flag

@sio.event
def disconnect():
    print('disconnected from server')


def emit_data(sio):
    global recording_flag
    # recording_flag = True
    max_width = 1200
    while True:
        if exit_flag.is_set():
            break
        if recording_flag:
            img = pyscreeze.screenshot()
            width, height = img.size
            # print("width {}, height {}".format(width, height))
            if width > max_width:
                new_width = max_width
                new_height = int(height * max_width / width)
                img = img.resize((new_width, new_height))
                # width, height = img.size
                # print("resized width {}, resized height {}".format(width, height))


            img = img.convert("RGB")
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            data_url = 'data:image/jpg;base64,' + base64.b64encode(buffered.getvalue()).decode('utf-8')
            # print(data_url)

            sio.emit('screen', data_url, namespace='/api')
            print('data emited')

        sleep(0.5)



def getComputerName():
        return win32api.GetComputerName()

def getUserName():
        return win32api.GetUserName()

def get_app_path(hwnd) -> Optional[str]:
    """Get application path given hwnd."""
    path = None
    process = None

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = win32api.OpenProcess(0x0400, False, pid) # PROCESS_QUERY_INFORMATION = 0x0400

        path = win32process.GetModuleFileNameEx(process, 0)
    except:
        pass
    finally:
        if process:
                win32api.CloseHandle(process)

    return path

def get_app_name(hwnd) -> Optional[str]:
    """Get application filename given hwnd."""
    path = get_app_path(hwnd)

    if path is None:
        return None
    
    return os.path.basename(path)

def get_window_title(hwnd):
    return win32gui.GetWindowText(hwnd)

def get_active_window_handle():
    hwnd = win32gui.GetForegroundWindow()
    return hwnd


def getRecordAndKeyStroke(keyboard, mouse):
        global user_id

        cur_dir = os.getcwd()
        dst_dir = os.path.join(cur_dir, "output")


        # temp_dir = os.path.join(cur_dir, "temp")
        # createFolder(temp_dir)
        # clearFolder(temp_dir)

        computer_name = getComputerName()
        now = datetime.now(pytz.timezone('Asia/Kolkata'))

        # Specify the desired format for the file name
        file_name_format = "%Y-%m-%d_%H-%M-%S"
        # Format the `now` variable as a string with the specified format
        formatted_now = now.strftime(file_name_format)


        dst_txt_name = os.path.join(dst_dir, "{}.txt".format(formatted_now))
        # dst_mov_name = os.path.join(dst_dir, "{}.mp4".format(formatted_now))
        # temp_mov_name = os.path.join(temp_dir, "{}.mp4".format(formatted_now))

        # recorder = pyscreenrec.ScreenRecorder()
        # recorder.start_recording(temp_mov_name, 25)

        previous_title = previous_app = ""
        last_run = now

        while True:
                if exit_flag.is_set():
                        print('disconnect from request')
                        break
                
                hwnd = get_active_window_handle()
                title = get_window_title(hwnd)
                app = get_app_name(hwnd)

                if not previous_title:
                        previous_title = title
                if not previous_app:
                      previous_app = app
                
                if previous_title == title and previous_app == app:
                        
                        sleep(1.0)
                        continue
                        
                
                now = datetime.now(pytz.timezone('Asia/Kolkata'))
             
                
                # If input:    Send a heartbeat with data, ensure the span is correctly set, and don't use pulsetime.
                # If no input: Send a heartbeat with all-zeroes in the data, use a pulsetime.
                # FIXME: Doesn't account for scrolling
                # FIXME: Counts both keyup and keydown
        
                keyboard_data = keyboard.next_event()
                keyboard_stroke = "".join(keyboard_data["data"])
                keyboard_count = keyboard_data["count"]
                print('total pressed keys: {}'.format(keyboard_stroke))

                mouse_data = mouse.next_event()
                mouse_count = mouse_data['count']

                print('key count: {} mouse count: {}'.format(keyboard_count, mouse_count))

                key_mouse_count = "{}/{}".format(keyboard_count, mouse_count)
                data_url = ""

                # try:
                #         recorder.stop_recording()
                #         compressMp4(temp_mov_name, dst_mov_name)

                #         # Open the MP4 file in binary mode and read its contents
                #         with open(dst_mov_name, "rb") as f:
                #                 mp4_data = f.read()

                #         # Encode the binary data as a Base64 string
                #         data_url = "data:video/webm;base64," + base64.b64encode(mp4_data).decode("utf-8")
                      
                # except:
                #         pass
                
                duration = int((now - last_run).total_seconds())
                last_run = now 
                # print(data_url)

                data = {
                        'user_id': user_id,
                        'start_time': "",
                        'screen_recording': data_url,
                        'computer_name': computer_name,
                        'keystrokes': keyboard_stroke,
                        'key_mouse_count': key_mouse_count,
                        'process_url': previous_app,
                        'duration': duration,
                        'app_webpage': previous_title
                }

                previous_title = title
                previous_app = app 

                # print('current time {}'.format(now.hour))
                # if now.hour >= 9 and now.hour < 17:
                response = requests.post(set_log_url, json=data)

                if response.status_code == 400:
                    print('Invalid credentials')
                else:
                    print("user id is {}".format(user_id))


                # Format the `now` variable as a string with the specified format
                formatted_now = now.strftime(file_name_format)
                dst_txt_name = os.path.join(dst_dir, "{}.txt".format(formatted_now))
                # dst_mov_name = os.path.join(dst_dir, "{}.mp4".format(formatted_now))
                # temp_mov_name = os.path.join(temp_dir, "{}.mp4".format(formatted_now))

                # recorder.start_recording(temp_mov_name, 25)

thread = None
emission_thread = None
keyboard = None
mouse = None

def terminate_threads():
    global thread, emission_thread, keyboard, mouse
    exit_flag.set()
    sleep(2.0)
    thread.join()
    print('main thread stopped')
    emission_thread.join()
    print('socket thread stopped')
    keyboard.stop()
    print('keyboard stopped')
    mouse.stop()
    print('mouse stopped')
    sleep(1.0)
     
def main():
    global user_id, sio, thread, emission_thread, keyboard, mouse
    
   
    flag = False
    

    config = configparser.ConfigParser()
    config.read('config.ini')

    email = config.get('DEFAULT', 'email')


            # check if user is in database
    data = { 
                    'email': email
                    }

    response = requests.post(authenticaion_url, json=data)

    if response.status_code == 400:
        print('Invalid credentials')
    else:
        user = response.json()
        user_id = user['_id']

        print('Login successful')


        keyboard = KeyboardListener()
        keyboard.start()

        mouse = MouseListener()
        mouse.start()

        thread = threading.Thread(target=getRecordAndKeyStroke, args=(keyboard, mouse,))
        thread.start()

        print('thread is created')

        sio.connect(socket_url)
        emission_thread = threading.Thread(target=emit_data, args=(sio,))
        emission_thread.start()

    # Register the termination function to be called on program exit
    atexit.register(terminate_threads)

        
        


if __name__ == '__main__':
    main()
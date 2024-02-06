

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

from typing import Optional, Dict

import json
import logging
import multiprocessing 

import socket

import socketio

import pyscreeze

from io import BytesIO
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

def createFolder(folder_path):
        if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print("Folder created successfully!")
        else:
                print("Folder already exists.")

def clearFolder(folder_path):
        items = os.listdir(folder_path)

        for item in items:
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                        os.remove(item_path)
                elif os.path.isdir(item_path):
                        os.rmdir(item_path)



def compressMp4(srcname, dstname):
        command = 'ffmpeg -nostdin -i {} -b 1000k {}'.format(srcname, dstname)
        result = subprocess.run(command)

def getComputerName():
        return socket.gethostname()


logger = logging.getLogger(__name__)
script = None


def compileScript():
    """
    Compiles the JXA script and caches the result.

    Resources:
     - https://stackoverflow.com/questions/44209057/how-can-i-run-jxa-from-swift
     - https://stackoverflow.com/questions/16065162/calling-applescript-from-python-without-using-osascript-or-appscript
    """

    # use a global variable to cache the compiled script for performance
    global script
    if script:
        return script

    from OSAKit import OSAScript, OSALanguage

    scriptPath = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "printAppStatus.jxa"
    )
    with open(scriptPath) as f:
        scriptContents = f.read()

        # remove shebang line
        if scriptContents.split("\n")[0].startswith("#"):
            scriptContents = "\n".join(scriptContents.split("\n")[1:])

    script = OSAScript.alloc().initWithSource_language_(
        scriptContents, OSALanguage.languageForName_("JavaScript")
    )
    success, err = script.compileAndReturnError_(None)

    # should only occur if jxa was modified incorrectly
    if not success:
        raise Exception(f"error compiling jxa script: {err['NSLocalizedDescription']}")

    return script


def getInfo():
    script = compileScript()
    
    result, err = script.executeAndReturnError_(None)
    
    if err:
        # error structure:
        # {
        #     NSLocalizedDescription = "Error: Error: Can't get object.";
        #     NSLocalizedFailureReason = "Error: Error: Can't get object.";
        #     OSAScriptErrorBriefMessageKey = "Error: Error: Can't get object.";
        #     OSAScriptErrorMessageKey = "Error: Error: Can't get object.";
        #     OSAScriptErrorNumberKey = "-1728";
        #     OSAScriptErrorRangeKey = "NSRange: {0, 0}";
        # }
        
        # raise Exception(f"jxa error: {err['NSLocalizedDescription']}")
        return {'title':"", 'app':""}

    return json.loads(result.stringValue())


def background_ensure_permissions() -> None:
    permission_process = multiprocessing.Process(target=ensure_permissions, args=(()))
    permission_process.start()

    return


def ensure_permissions() -> None:
    # noreorder
    from AppKit import (  # fmt: skip
        NSURL,
        NSAlert,
        NSAlertFirstButtonReturn,
        NSWorkspace,
    )
    from ApplicationServices import AXIsProcessTrusted  # fmt: skip

    accessibility_permissions = AXIsProcessTrusted()
    if not accessibility_permissions:
        logger.info("No accessibility permissions, prompting user")
        title = "Missing accessibility permissions"
        info = "To let ActivityWatch capture window titles grant it accessibility permissions. \n If you've already given ActivityWatch accessibility permissions and are still seeing this dialog, try removing and re-adding them."

        alert = NSAlert.new()
        alert.setMessageText_(title)
        alert.setInformativeText_(info)

        alert.addButtonWithTitle_("Open accessibility settings")
        alert.addButtonWithTitle_("Close")

        choice = alert.runModal()
        if choice == NSAlertFirstButtonReturn:
            NSWorkspace.sharedWorkspace().openURL_(
                NSURL.URLWithString_(
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
                )
            )

def startKeyListner(keyboard):
        keyboard.start()

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

        # recorder = ScreenRecorder()
        # recorder.start_recording(temp_mov_name, 25)

        previous_title = previous_app = ""
        last_run = now
                      

        while True:
                
                if exit_flag.is_set():
                        print('disconnect from request')
                        break

                info = getInfo()
                title = ""
                if 'title' in info.keys():
                        title = info['title']
                app = info["app"]
                
                # print("title {}, app {}".format(title, app))
  
                
                if not previous_title:
                        previous_title = title
                if not previous_app:
                      previous_app = app
                
                if previous_app != "Terminal":
                    if previous_title == title and previous_app == app:
                        sleep(1.0)
                        continue
                else:
                    if previous_app == app:
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


                #if response.status_code == 400:
                #        print('Invalid credentials')
                #else:
                #        print("user id is {}".format(user_id))
                #        if not user_id:
                #                user_id = response.json()



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

def terminate_threads():
    global thread, emission_thread
    exit_flag.set()
    sleep(2.0)
    thread.join()
    print('main thread stopped')
    emission_thread.join()
    print('socket thread stopped')
    # keyboard.stop()
    print('keyboard stopped')
    sleep(1.0)


def main():
    global user_id, sio, thread, emission_thread

    keyboard = None

    config = configparser.ConfigParser()
    # Get the current directory of the Python script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the path to the config.ini file in the parent folder
    config_path = os.path.join(os.path.dirname(current_dir), 'config.ini')
    config.read(config_path)
    # config.read('config.ini')

    email = config.get('DEFAULT', 'email')
    print('email: ', email)


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
        
        background_ensure_permissions()
        print('background permission')

        keyboard = KeyboardListener()
        keyboard.start()

        sleep(1)
        mouse = MouseListener()
        mouse.start()
                                            
        print('keyboard is created')

                    
        thread = threading.Thread(target=getRecordAndKeyStroke, args=(keyboard, mouse,))
        thread.start()

        print('thread is created')

        sio.connect(socket_url)
        emission_thread = threading.Thread(target=emit_data, args=(sio,))
        emission_thread.start()


    # Register the termination function to be called on program exit
    atexit.register(terminate_threads)

if __name__ == '__main__':
    # Pyinstaller fix
    multiprocessing.freeze_support()
    main()
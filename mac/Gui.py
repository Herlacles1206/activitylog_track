
import PySimpleGUI as sg

from time import sleep
from datetime import datetime, timezone
import pytz

from listener import KeyboardListener

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


# Define a flag or event to signal the thread to exit
exit_flag = threading.Event()

local_url = 'localhost'
server_url = '144.126.254.71'

set_log_url = f'http://{server_url}:5000/api/activitylog/setlog'
authenticaion_url = f'http://{server_url}:5000/api/users/login'
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
    max_width = 800
    while True:
        if exit_flag.is_set():
            break
        if recording_flag:
            img = pyscreeze.screenshot()
            width, height = img.size
            print("width {}, height {}".format(width, height))
            if width > max_width:
                new_width = max_width
                new_height = int(height * max_width / width)
                img = img.resize((new_width, new_height))
                width, height = img.size
                print("resized width {}, resized height {}".format(width, height))


            buffered = BytesIO()
            img.save(buffered, format="png") 
            data_url = 'data:image/png;base64,' + base64.b64encode(buffered.getvalue()).decode('utf-8')
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
        os.path.dirname(os.path.realpath(__file__)), "printAppStatus.jxa"
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


def getInfo() -> Dict[str, str]:
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

        raise Exception(f"jxa error: {err['NSLocalizedDescription']}")

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

def getRecordAndKeyStroke(keyboard):
        global user_id

        cur_dir = os.getcwd()
        dst_dir = os.path.join(cur_dir, "output")
        
        createFolder(dst_dir)
        clearFolder(dst_dir)
        # temp_dir = os.path.join(cur_dir, "temp")
        # createFolder(temp_dir)
        # clearFolder(temp_dir)
        print('create folder')

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
        keyboard.next_event()

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
                
                if previous_title == title and previous_app == app:
                        sleep(1.0)
                        continue
                        
                
                now = datetime.now(pytz.timezone('Asia/Kolkata'))
             
                
                # If input:    Send a heartbeat with data, ensure the span is correctly set, and don't use pulsetime.
                # If no input: Send a heartbeat with all-zeroes in the data, use a pulsetime.
                # FIXME: Doesn't account for scrolling
                # FIXME: Counts both keyup and keydown
        
                keyboard_data = keyboard.next_event()
                keyboard_data = "".join(keyboard_data)

                print('total pressed keys: {}'.format(keyboard_data))

                with open(dst_txt_name, 'w') as fp:
                        fp.write(keyboard_data)

                
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
                        'keystrokes': keyboard_data,
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

                # Format the `now` variable as a string with the specified format
                formatted_now = now.strftime(file_name_format)
                dst_txt_name = os.path.join(dst_dir, "{}.txt".format(formatted_now))
                # dst_mov_name = os.path.join(dst_dir, "{}.mp4".format(formatted_now))
                # temp_mov_name = os.path.join(temp_dir, "{}.mp4".format(formatted_now))

                # recorder.start_recording(temp_mov_name, 25)



def main():
    global user_id, sio

    keyboard = KeyboardListener()
    keyboard.start()


    menu = ['', ['Show Window', 'Hide Window', '---', '!Disabled Item', 'Change Icon', ['Happy', 'Sad', 'Plain'], 'Exit']]
    tooltip = 'Activity Tracker'

    layout = [[sg.Text('                     Activity log tracking App')],
              [sg.T('Email:      '), sg.Input(key='-EMAIL-', s=(20,1))],
              [sg.T('Password:'), sg.Input(key='-PASSWORD-', s=(20,1))],
              [sg.Text(size=(15,1)), sg.B('Login')],
              [sg.Multiline(size=(40,10), reroute_stdout=False, reroute_cprint=True, write_only=True, key='-OUT-')],
              [sg.Text(size=(16,1)), sg.Button('Exit')]]

    window = sg.Window('Window Title', layout, finalize=True, enable_close_attempted_event=True)


    # tray = SystemTray(menu, single_click_events=False, window=window, tooltip=tooltip, icon=sg.DEFAULT_BASE64_ICON)
    # tray.show_message('System Tray', 'System Tray Icon Started!')
    # sg.cprint(sg.get_versions())
    
    flag = False
    thread = None
    emission_thread = None
    

    while True:
        event, values = window.read()

        # IMPORTANT step. It's not required, but convenient. Set event to value from tray
        # if it's a tray event, change the event variable to be whatever the tray sent
        # if event == tray.key:
        #     sg.cprint(f'System Tray Event = ', values[event], c='white on red')
        #     event = values[event]       # use the System Tray's event as if was from the window

        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        # sg.cprint(event, values)
        # tray.show_message(title=event, message=values)

        if event in ('Show Window', sg.EVENT_SYSTEM_TRAY_ICON_DOUBLE_CLICKED):
            window.un_hide()
            window.bring_to_front()
        elif event in ('Hide Window', sg.WIN_CLOSE_ATTEMPTED_EVENT):
            window.hide()
        #     tray.show_icon()        # if hiding window, better make sure the icon is visible
            # tray.notify('System Tray Item Chosen', f'You chose {event}')
        # elif event == 'Happy':
        #     tray.change_icon(sg.EMOJI_BASE64_HAPPY_JOY)
        # elif event == 'Sad':
        #     tray.change_icon(sg.EMOJI_BASE64_FRUSTRATED)
        # elif event == 'Plain':
        #     tray.change_icon(sg.DEFAULT_BASE64_ICON)
        # elif event == 'Hide Icon':
        #     tray.hide_icon()
        # elif event == 'Show Icon':
        #     tray.show_icon()
        # elif event == 'Change Tooltip':
        #     tray.set_tooltip(values['-IN-'])
        elif event == 'Login':
            email = values['-EMAIL-']
            pwd = values['-PASSWORD-']

            # check if user is in database
            data = { 
                    'email': email,
                    'password': pwd
                    }

            response = requests.post(authenticaion_url, json=data)

            if response.status_code == 400:
                    sg.cprint('Invalid credentials', c='white on red')
            else:
                    user = response.json()
                    user_id = user['_id']

                    sg.cprint('Login successful')
                    print('Login successful')

                    background_ensure_permissions()
                    print('background permission')

                    
                                            
                    print('keyboard is created')

                    
                    thread = threading.Thread(target=getRecordAndKeyStroke, args=(keyboard,))
                    thread.start()


                    sg.cprint('thread is created')
                    print('thread is created')

                    sio.connect(socket_url)
                    emission_thread = threading.Thread(target=emit_data, args=(sio,))
                    emission_thread.start()

                    flag = True


    # if thread is created, terminate threads 
    if flag:
        exit_flag.set()
        sleep(2.0)
        # keyboard.stop()
        thread.join()
        emission_thread.join()
        sleep(1.0)

#     tray.close()            # optional but without a close, the icon may "linger" until moused over
    window.close()

if __name__ == '__main__':
    # Pyinstaller fix
    multiprocessing.freeze_support()
    main()
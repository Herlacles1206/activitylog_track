from time import sleep
from datetime import datetime, timezone
import pytz

from listener import KeyboardListener

import pyscreenrec
import os

import threading
import sys

import base64
import requests

import subprocess

import win32api

# Define a flag or event to signal the thread to exit
exit_flag = threading.Event()
set_log_url = 'http://localhost:5000/api/activitylog/setlog'
authenticaion_url = 'http://localhost:5000/api/users/login'


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
        command = 'ffmpeg -i {} -b 1000k {}'.format(srcname, dstname)
        result = subprocess.run(command)

def getComputerName():
        return win32api.GetComputerName()

def getUserName():
        return win32api.GetUserName()


def getRecordAndKeyStroke():
        global email, user_id

        cur_dir = os.getcwd()
        dst_dir = os.path.join(cur_dir, "output")
        temp_dir = os.path.join(cur_dir, "temp")
        createFolder(dst_dir)
        createFolder(temp_dir)

        now = datetime.now(pytz.timezone('Asia/Kolkata'))

        # Specify the desired format for the file name
        file_name_format = "%Y-%m-%d_%H-%M-%S"
        # Format the `now` variable as a string with the specified format
        formatted_now = now.strftime(file_name_format)


        dst_txt_name = os.path.join(dst_dir, "{}.txt".format(formatted_now))
        dst_mov_name = os.path.join(dst_dir, "{}.mp4".format(formatted_now))
        temp_mov_name = os.path.join(temp_dir, "{}.mp4".format(formatted_now))

        recorder = pyscreenrec.ScreenRecorder()
        recorder.start_recording(temp_mov_name, 25)

        poll_time = 10

        
        while True:
                last_run = now

                # we want to ensure that the polling happens with a predictable cadence
                time_to_sleep = poll_time - datetime.now(pytz.timezone('Asia/Kolkata')).timestamp() % poll_time
                # ensure that the sleep time is between 0 and poll_time (if system time is changed, this might be negative)
                time_to_sleep = max(min(time_to_sleep, poll_time), 0)
                sleep(time_to_sleep)

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

                recorder.stop_recording()

                compressMp4(temp_mov_name, dst_mov_name)

                # Open the MP4 file in binary mode and read its contents
                with open(dst_mov_name, "rb") as f:
                        mp4_data = f.read()

                # Encode the binary data as a Base64 string
                data_url = "data:video/webm;base64," + base64.b64encode(mp4_data).decode("utf-8")
                # print(data_url)

                data = {
                        'user_id': user_id,
                        'email': email,
                        'start_time': "",
                        'screen_recording': data_url,
                        'keystrokes': keyboard_data,
                        'process_url':"",
                        'duration': "",
                        'app_webpage': ""
                }

                response = requests.post(set_log_url, json=data)

                if response.status_code == 400:
                        print('Invalid credentials')
                else:
                        print("user id is {}".format(user_id))
                        if not user_id:
                                user_id = response.json()

                
                clearFolder(dst_dir)
                clearFolder(temp_dir)

                if exit_flag.is_set():
                        break

                if now.hour < 9 or now.hour >= 17:
                        continue

                # Format the `now` variable as a string with the specified format
                formatted_now = now.strftime(file_name_format)
                dst_txt_name = os.path.join(dst_dir, "{}.txt".format(formatted_now))
                dst_mov_name = os.path.join(dst_dir, "{}.mp4".format(formatted_now))
                temp_mov_name = os.path.join(temp_dir, "{}.mp4".format(formatted_now))

                recorder.start_recording(temp_mov_name, 25)

if __name__ == '__main__':

        email = 'user2@gmail.com'
        pwd = '123'
        user_id = ''
        flag = False

        # check if user is in database
        data = { 
                'email': email,
                'password': pwd
                }

        response = requests.post(authenticaion_url, json=data)

        if response.status_code == 400:
                print('Invalid credentials')
        else:
                user = response.json()
                user_id = user['_id']
                flag = True
                print('user id is {}'.format(user_id))


        if flag:
                keyboard = KeyboardListener()
                keyboard.start()


                thread = threading.Thread(target=getRecordAndKeyStroke)
                thread.start()

                print('thread is created')
                start = datetime.now(pytz.timezone('Asia/Kolkata'))

                while True:
                        end = datetime.now(pytz.timezone('Asia/Kolkata'))

                        elapsed_seconds = (end - start).total_seconds()
                        print(elapsed_seconds)

                        if (elapsed_seconds > 50):
                                exit_flag.set()
                                keyboard.stop()
                                thread.join()
                                print('thread is finished')
                                break
                        else:
                                sleep(1)



        





        

        
        

        
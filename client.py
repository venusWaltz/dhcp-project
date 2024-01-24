#!/usr/bin/env python3
import uuid
import socket
from datetime import datetime
import sys

# Extract local MAC address [DO NOT CHANGE]
MAC = ":".join(["{:02x}".format((uuid.getnode() >> ele) & 0xFF) for ele in range(0, 8 * 6, 8)][::-1]).upper()

# SERVER IP AND PORT NUMBER [DO NOT CHANGE VAR NAMES]
SERVER_IP = "10.0.0.100"
SERVER_PORT = 9000

mac, ip, timestamp = None, None, None
timeout_seconds = 5

# --------------------------------- client operations  ---------------------------------
               
def client_operation(message):
    global response, mac, ip, timestamp
    if message[0] == "DECLINE":
        handle_decline()

    elif message != None:
        # store response data
        response = message
        mac, ip, timestamp = response[1], response[2], datetime.fromisoformat(response[3])

        if message[0] == "OFFER":
            client_operation(handle_offer())
        elif message[0] == "ACKNOWLEDGE":
            handle_acknowledge()

# --------------------------------- sending messages ---------------------------------

def send_discover_message():
    print("client: sending DISCOVER message")
    message = "DISCOVER " + MAC
    clientSocket.sendto(message.encode(), (SERVER_IP, SERVER_PORT))

def send_message(msg_type):
    print("client: sending", msg_type, "message")
    message = f"{msg_type} {MAC} {ip} {timestamp}"
    clientSocket.sendto(message.encode(), (SERVER_IP, SERVER_PORT))

# --------------------------------- receiving messages ---------------------------------

def handle_offer():
    # check if MAC in message matches client MAC address
    if mac == MAC:
        print("client: MAC address in message matches client MAC")

        # if not yet expired
        if timestamp > datetime.now():
            print("client: timestamp is not yet expired")
            send_message("REQUEST")         # send REQUEST message
            return listen_for_response()    # listen for response
        
        else:
            print("client: timestamp has expired")
            retry = input("lease has expired. retry? (Y/N) ").upper()
            if retry == "Y":
                send_discover_message()     # send discover message
                return listen_for_response()
            else:
                terminate_program("client chose to quit")
    else:
        print("client: MAC address in OFFER message does not match client MAC address")


def handle_decline():
    terminate_program("request was denied by the server")

def handle_acknowledge():
    # check if MAC in message matches client MAC address
    if mac != MAC:
        terminate_program("MAC address in ACKNOWLEDGE message does not match client MAC address")
    else:
        print("client: IP address", ip, "assigned to client with MAC address", mac, "will expire at", timestamp)

# --------------------------------- menu ---------------------------------

def display_menu():
    print("\nmenu:")
    print("1. release")
    print("2. renew")
    print("3. quit")

def handle_menu_select():
    select = input("enter your selection: ")
    if select == "1":
        send_message("RELEASE")
    elif select == "2":
        send_message("RENEW")
        client_operation(listen_for_response())
    elif select == "3":
        terminate_program("client chose to quit")
    else:
        print("please enter 1 , 2, or 3")

# --------------------------------- helper methods ---------------------------------

def listen_for_response():
    print("client: listening for response")
    clientSocket.settimeout(timeout_seconds)
    try:
        message, _ = clientSocket.recvfrom(4096)
        print("\nclient: received message:", message.decode())
        return message.decode().split()
    except socket.timeout:
        terminate_program("failed to receive response from server within specified time")

def terminate_program(message):
    print("client:", message)
    clientSocket.close()
    sys.exit()

# --------------------------------- main program ---------------------------------

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

send_discover_message()             # send DISCOVER message
response = listen_for_response()    # listen for response
client_operation(response)          # handle response received from server

# display menu
while True:
    display_menu()
    handle_menu_select()
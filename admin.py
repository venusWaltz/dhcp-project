#!/usr/bin/env python3
import uuid
import socket
from datetime import datetime
import sys
import pickle

class Record:
    def __init__(self, record_num, ip_address):
        self.record_num = record_num
        self.mac_address = None
        self.ip_address = ip_address
        self.timestamp = None
        self.acked = False

    def to_string(self):
        return f"{self.record_num}\t{self.mac_address}\t{self.ip_address}\t{self.timestamp}\t{self.acked}"

# Extract local MAC address [DO NOT CHANGE]
MAC = ":".join(["{:02x}".format((uuid.getnode() >> ele) & 0xFF) for ele in range(0, 8 * 6, 8)][::-1]).upper()

# SERVER IP AND PORT NUMBER [DO NOT CHANGE VAR NAMES]
SERVER_IP = "10.0.0.100"
SERVER_PORT = 9000

adminSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# send LIST message
message = "LIST"
adminSocket.sendto(message.encode(), (SERVER_IP, SERVER_PORT))

# receive response data from server
message, _ = adminSocket.recvfrom(4096)
data = pickle.loads(message)

# print list
i = 0
for record in data:
    if record.acked == True and datetime.fromisoformat(record.timestamp) > datetime.now():
        if i == 0:
            print("Record\tMAC Address\t\tIP Address\tTimestamp\t\t\tAcked")
        print(record.to_string())
        i+=1
if i == 0:
    print("admin: no active clients found on server")
#!/usr/bin/env python3
import socket
from ipaddress import IPv4Interface
from datetime import datetime, timedelta
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

# List containing all available IP addresses as strings
ip_addresses = [ip.exploded for ip in IPv4Interface("192.168.45.0/28").network.hosts()]

# initialize list of records
records = []
for i, ip in enumerate(ip_addresses, start=1):
    records.append(Record(i, ip))

# Calculate response based on message
def dhcp_operation(parsed_message):
    if parsed_message[0] == "LIST":
        return handle_list()
    elif parsed_message[0] == "DISCOVER":
        return handle_discover(parsed_message[1:])
    elif parsed_message[0] == "REQUEST":
        return handle_request(parsed_message[1:])
    elif parsed_message[0] == "RELEASE":
        return handle_release(parsed_message[1:])
    elif parsed_message[0] == "RENEW":
        return handle_renew(parsed_message[1:])

# ------------------------------------------------------------------------------------
# --------------------------------- sending messages ---------------------------------
# ------------------------------------------------------------------------------------

def decline_message():
    print("server: sending DECLINE message")
    return "DECLINE"

def offer_message(record):
    print("server: sending OFFER message")
    return f"OFFER {record.mac_address} {record.ip_address} {record.timestamp}"

def acknowledge_message(record):
    print("server: sending ACKNOWLEDGE message")
    return f"ACKNOWLEDGE {record.mac_address} {record.ip_address} {record.timestamp}"

# --------------------------------------------------------------------------------------
# --------------------------------- receiving messages ---------------------------------
# --------------------------------------------------------------------------------------

# ---------------------------------------- LIST ----------------------------------------
def handle_list():
    data = pickle.dumps(records)
    server.sendto(data, clientAddress)
    
# -------------------------------------- DISCOVER --------------------------------------
def handle_discover(parsed_message):
    mac_address = parsed_message[0]
    print("server: client with MAC address", mac_address, "is discovering")

    # check if MAC exists in list of assigned IP addresses
    found = find_record_by_mac(mac_address)

    if found:
        print("server: client was found in records")

        # if timestamp has not expired
        if datetime.fromisoformat(found.timestamp) > datetime.now():
            found.acked = True                  # set acked to true
            return acknowledge_message(found)   # send ACKNOWLEDGE message
        # if timestamp has expired, use same IP
        else:
            reset_lease(found)          # update record for expired lease
            print("server: timestamp for record with MAC address", mac_address, "and IP", record.ip_address, "is expired")
            return offer_message(found) # send OFFER message

    else:
        record = find_new_ip_address()  # look for available IP address

        # if a spot is found, update the record
        if record != None:
            update_record(record, mac_address)
            print("server: found available IP address " + record.ip_address)
            return offer_message(record)    # send OFFER message
        else:
            print("server: no available IP addresses")
            return decline_message()    # send DECLINE message

# --------------------------------------- REQUEST --------------------------------------
def handle_request(parsed_message):
    mac_address = parsed_message[0]
    ip_address = parsed_message[1]

    # check if IP has been assigned to client + if IP in message matches IP in record
    assigned = is_IP_assigned(mac_address, ip_address)

    if assigned == None:
        print("server: no IP has been assigned to client with MAC address " + mac_address)
        return decline_message()    # send DECLINE message

    # otherwise, check if timestamp has expired
    else:
        if datetime.fromisoformat(assigned.timestamp) < datetime.now():
            print("server: timestamp for record with MAC address", mac_address, "and IP", ip_address, "is expired")
            return decline_message()    # send DECLINE message
        else:
            assigned.acked = True   # set acked to true
            print("server: assigned IP address", ip_address, "to client with MAC address " + mac_address)
            return acknowledge_message(assigned)    # send ACKNOWLEDGE message

# --------------------------------------- RELEASE --------------------------------------
def handle_release(parsed_message):
    mac_address = parsed_message[0]
    
    # check if client MAC is in records
    record = find_record_by_mac(mac_address)

    if record:
        release_ip_address(record)
        print("server: released IP address assigned to client with MAC address", mac_address)
    else: 
        print("server: client with MAC address", mac_address, "has already been released")

# ---------------------------------------- RENEW ---------------------------------------
def handle_renew(parsed_message):
    mac_address = parsed_message[0]
    ip_address = parsed_message[1]
    print("server: client with MAC address", mac_address, "is renewing")

    # find the record for the client
    record = find_record_by_mac(mac_address)

    if record:
        print("server: client is in records")
        renew_ip_address(record)
        print("server: renewed IP address", ip_address, "of client with MAC address", mac_address)
        return acknowledge_message(record)  # send ACKNOWLEDGE message
        
    else:
        print("server: client not found in records")
        available = find_new_ip_address()   # look for available IP address

        # if a record is available, take it
        if available != None:
            release_ip_address(available)       # remove old record
            store_new_record(available, mac_address, ip_address)
            print("server: stored new IP address", ip_address, "of client with MAC address", mac_address)
            return offer_message(available)    # send OFFER message
        else:
            return decline_message()        # send DECLINE message

# --------------------------------------------------------------------------------------
# ----------------------------------- helper methods -----------------------------------
# --------------------------------------------------------------------------------------

def find_record_by_mac(target_mac):
    for record in records:
        if record.mac_address == target_mac:
            return record
    return None

def find_available_ip():
    for record in records:
        if record.mac_address == None:
            return record
    return None

def find_expired_ip():
    for record in records:
        if datetime.fromisoformat(record.timestamp) < datetime.now():
            return record
    return None

def find_new_ip_address():
    record = find_available_ip() # look for an available IP address
    if record == None:           # if there are no available IP addresses
        record = find_expired_ip()  # look for an expired IP address
    return record

def is_IP_assigned(target_mac, target_ip):
    for record in records:
        if record.mac_address == target_mac and record.ip_address == target_ip:
            return record
    return None

def update_timestamp(target_record):
    target_record.timestamp = (datetime.now() + timedelta(seconds=60)).isoformat()

def reset_lease(target_record):
    update_timestamp(target_record)             # update timestamp
    target_record.acked = False                 # set acked to False
    
def release_ip_address(target_record):
    target_record.mac_address = None                        # clear MAC address
    target_record.timestamp = datetime.now().isoformat()    # reset timestamp
    target_record.acked = False                             # set acked to False

def renew_ip_address(target_record):
    update_timestamp(target_record)   # update timestamp
    target_record.acked = True                  # set acked to False

def store_new_record(target_record, target_mac, target_ip):
    target_record.mac_address = target_mac      # set MAC address
    target_record.ip_address = target_ip        # set IP address
    reset_lease(target_record)                     # update timestamp and set acked to False

def update_record(target_record, target_mac):
    target_record.mac_address = target_mac  # set MAC address
    reset_lease(target_record)              # update timestamp and set acked to False

# --------------------------------------------------------------------------------------
# ------------------------------------ main program ------------------------------------
# --------------------------------------------------------------------------------------

# Start a UDP server
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Avoid TIME_WAIT socket lock [DO NOT REMOVE]
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("", 9000))
print("DHCP Server running...")

try:
    while True:
        message, clientAddress = server.recvfrom(4096)
        print("\nserver: received message:", message.decode())
        parsed_message = message.decode().split()
        response = dhcp_operation(parsed_message)
        if response:
            server.sendto(response.encode(), clientAddress)
except OSError:
    pass
except KeyboardInterrupt:
    pass

server.close()
import socket 
import selectors 
import random
import queue 
from datetime import datetime
import sys 
import time 
import threading 
import types 
import struct

host, machine_number = sys.argv[1], int(sys.argv[2])
machines = {1: 11112, 2: 22223, 3: 33334}
port = machines[machine_number]

others = list(machines.values())
others.remove(port)

messages = queue.Queue() 

def recvall(sock, n): 
    data = bytearray() 
    while len(data) < n: 
        packet = sock.recv(n - len(data))
        if not packet:
            return None 
        data.extend(packet) 
    return data

class Server(): 

    def __init__(self): 
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.lsock.bind((host, port))
        self.lsock.listen() 
        self.lsock.setblocking(False) 

        self.sel = selectors.DefaultSelector() 
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)

    def accept_wrapper(self): 
        conn, addr = self.lsock.accept() 
        conn.setblocking(False) 
        data = types.SimpleNamespace(addr=addr, time="")
        self.sel.register(conn, selectors.EVENT_READ, data=data)

    def service_connection(self, key, mask): 
        sock, data = key.fileobj, key.data
        raw_time = recvall(sock, 4)
        time = struct.unpack('>I', raw_time)[0]
        messages.put(time)
        
    def run(self): 
        while True: 
            events = self.sel.select(timeout=None) 
            for key, mask in events: 
                if key.data is None: 
                    self.accept_wrapper() 
                else: 
                    self.service_connection(key, mask)

class Client(): 

    def __init__(self):
        time.sleep(5)
        
        self.connections = {}
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock1.setblocking(True)
        self.sock1.connect((host, others[0])) 
        print(f"Connecting to {others[0]}!")
        self.connections[others[0]] = self.sock1

        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock2.setblocking(True) 
        self.sock2.connect((host, others[1]))
        print(f"Connecting to {others[1]}!")
        self.connections[others[1]] = self.sock2

        self.logical_clock = 0 
        self.tick = random.randint(1, 6)
    
    def read_message(self): 
        if not messages.empty(): 
            time = messages.get() 
            self.logical_clock = max(self.logical_clock, int(time)) + 1
            with open("log.txt", "a") as f: 
                f.write("Received a message: " + "Current system time: " + datetime.now().strftime("%H:%M:%S") + " Messages queue size: " + str(messages.qsize()) + " Logical clock time: " + str(self.logical_clock))
            return True 
        return False
            
    def write_message(self, port): 
        self.connections[port].sendall(struct.pack('>I', self.logical_clock))
        self.logical_clock += 1
        with open("log.txt", "a") as f: 
            f.write("Sent a message: " + "Current system time " + datetime.now().strftime("%H:%M:%S") + " Logical clock time " + str(self.logical_clock))
    
    def internal_event(self): 
        self.logical_clock += 1
        with open("log.txt", "a") as f: 
            f.write("Internal event: " + datetime.now().strftime("%H:%M:%S") + str(self.logical_clock))

    def run(self): 
        while True: 
            time.sleep(2)
            if not self.read_message(): 
                val = random.randint(1, 10) 
                if val == 1 or val == 2: 
                    self.write_message(others[val - 1])
                elif val == 3: 
                    for port in others: 
                        self.write_message(port) 
                else:
                    self.internal_event 


if __name__ == '__main__': 
    threading.Thread(target = Server().run).start() 
    threading.Thread(target = Client().run).start() 
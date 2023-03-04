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
from multiprocessing import Process

# Todos - get the timing right (run something once per self.tick seconds)
# Make things neater 

def recvall(sock, n): 
    data = bytearray() 
    while len(data) < n: 
        packet = sock.recv(n - len(data))
        if not packet:
            return None 
        data.extend(packet) 
    return data

class Machine(): 
    def __init__(self, config): 
        self.messages = []
        self.config = config 
    
    def run(self): 
        threading.Thread(target = Server(self.config, self.messages).run).start() 
        time.sleep(5)
        threading.Thread(target = Client(self.config, self.messages).run).start() 


class Server(): 

    def __init__(self, config, messages): 
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.lsock.bind((config[0], config[1]))
        self.lsock.listen() 
        self.lsock.setblocking(False) 

        self.sel = selectors.DefaultSelector() 
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)
        self.messages = messages

    def accept_wrapper(self): 
        conn, addr = self.lsock.accept() 
        conn.setblocking(False) 
        data = types.SimpleNamespace(addr=addr)
        self.sel.register(conn, selectors.EVENT_READ, data=data)

    def service_connection(self, key, mask): 
        sock = key.fileobj
        raw_time = recvall(sock, 4)
        time = struct.unpack('>I', raw_time)[0]
        self.messages.append(time)
        
    def run(self): 
        while True: 
            events = self.sel.select(timeout=None) 
            for key, mask in events: 
                if key.data is None: 
                    self.accept_wrapper() 
                else: 
                    self.service_connection(key, mask)

class Client(): 

    def __init__(self, config, messages):
        self.connections = {}
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock1.setblocking(True)
        self.sock1.connect((config[0], config[2])) 
        print(f"{config[1]} connecting to {config[2]}!")
        self.connections[config[2]] = self.sock1

        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock2.setblocking(True) 
        self.sock2.connect((config[0], config[3]))
        print(f"{config[1]} connecting to {config[3]}!")
        self.connections[config[3]] = self.sock2

        self.logical_clock = 0 
        self.tick = random.randint(1, 6)
        self.config = config
        self.messages = messages
    
    def read_message(self): 
        if self.messages: 
            time = self.messages.pop() 
            self.logical_clock = max(self.logical_clock, int(time)) + 1
            with open("log.txt", "a") as f: 
                f.write("Received a message: " + "Current system time: " + datetime.now().strftime("%H:%M:%S") + " Messages queue size: " + str(len(self.messages)) + " Logical clock time: " + str(self.logical_clock))
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
                    self.write_message(self.config[val + 1])
                elif val == 3: 
                    for port in self.config[2:]: 
                        self.write_message(port) 
                else:
                    self.internal_event 


if __name__ == '__main__': 
    port1 = 11113
    port2 = 22224
    port3 = 33335

    config1 = ["", port1, port2, port3]
    p1 = Process(target=Machine(config1).run, args=())
    config2 = ["", port2, port1, port3]
    p2 = Process(target=Machine(config2).run)
    config3 = ["", port3, port1, port2]
    p3 = Process(target=Machine(config3).run)
    
    p1.start()
    p2.start()
    p3.start()
    
    p1.join()
    p2.join()
    p3.join()
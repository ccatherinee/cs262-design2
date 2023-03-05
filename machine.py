import socket, selectors, types, struct
import random, time, threading
from datetime import datetime
from multiprocessing import Process


# Class representing each of the 3 model machines
class Machine(): 
    def __init__(self, config): 
        self.messages = [] # message queue containing other machines' timestamps
        self.config = config # network config of the form [host, listening port, port to connect to, port to connect to]
    
    def run(self): 
        threading.Thread(target = Server(self.config, self.messages).run).start() # start "server" component of machine
        time.sleep(5) # ensure all machines are up and listening properly
        threading.Thread(target = Client(self.config, self.messages).run).start() # start "client" component of machine


# Each machine has a "server" component represented by this class, responsible for
# accepting connections from other machines and constantly receiving messages into the queue
class Server(): 
    def __init__(self, config, messages): 
        # Establish listening socket so that other machines can connect
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.lsock.bind((config[0], config[1]))
        self.lsock.listen() 
        self.lsock.setblocking(False) 

        # Register read events from listening socket in selector so we know when another machine wants to connect
        self.sel = selectors.DefaultSelector() 
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)
        self.messages = messages

    # Accepts new connection from another machine, registering read events from that socket 
    # in selector, so that we know when there are messages to receive into messages queue
    def accept_wrapper(self): 
        conn, addr = self.lsock.accept() 
        conn.setblocking(False) 
        data = types.SimpleNamespace(addr=addr)
        self.sel.register(conn, selectors.EVENT_READ, data=data)

    # Receives timestamp message from connection and enqueues into message queue
    def service_connection(self, key, mask): 
        sock = key.fileobj
        raw_time = self.recvall(sock, 4)
        time = int(struct.unpack('>I', raw_time)[0])
        self.messages.append(time)
        
    # Helper function that receives all n bytes from specified socket
    def recvall(self, sock, n): 
        data = bytearray() 
        while len(data) < n: 
            packet = sock.recv(n - len(data))
            if not packet: return None 
            data.extend(packet) 
        return data

    # Main loop that listens for socket activity
    def run(self): 
        while True: 
            events = self.sel.select(timeout=None) 
            for key, mask in events: 
                if key.data is None: # no data means new connection to accept
                    self.accept_wrapper() 
                else: # data existing means old connection/machine sending a message that we should receive
                    self.service_connection(key, mask)


# Each machine also has a "client" component represented by this class, responsible for
# connecting to other machines and reading messages from the queue, sending messages, or doing internal events
class Client(): 
    def __init__(self, config, messages):
        # Connect to other 2 machines
        self.sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock1.setblocking(True)
        self.sock1.connect((config[0], config[2])) 
        print(f"Machine {config[1]} connected to machine {config[2]}!")
        self.sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock2.setblocking(True) 
        self.sock2.connect((config[0], config[3]))
        print(f"Machine {config[1]} connected to machine {config[3]}!")

        # Store network configuration/connections and messages queue
        self.config = config
        self.messages = messages
        self.connections = {config[2]: self.sock1, config[3]: self.sock2}

        # Initialize logical clock and clock tick rate
        self.logical_clock = 0 
        self.tick = random.randint(1, 6)
        print(f"Machine {config[1]} has tick rate {self.tick}")
    
    # Reads a message from the message queue if queue non-empty, updating logical clock
    # as appropriate, and returns True; otherwise, does nothing and returns False
    def read_message(self): 
        if not self.messages: 
            return False
        time = self.messages.pop() 
        self.logical_clock = max(self.logical_clock, time) + 1
        with open(f"log{self.config[1]}.txt", "a+") as f: 
            f.write("Received a message: system time " + datetime.now().strftime("%H:%M:%S:%f") + ", logical clock time " + str(self.logical_clock) + ", remaining message queue size " + str(len(self.messages)) + "\n")
        return True
            
    # Sends message to machine at specified port, incrementing logical clock
    def write_message(self, port): 
        self.logical_clock += 1
        self.connections[port].sendall(struct.pack('>I', self.logical_clock))
        with open(f"log{self.config[1]}.txt", "a+") as f: 
            f.write("Sent a message: system time " + datetime.now().strftime("%H:%M:%S%f") + ", logical clock time " + str(self.logical_clock) + "\n")
    
    # Performs internal event, incrementing logical clock
    def internal_event(self): 
        self.logical_clock += 1
        with open(f"log{self.config[1]}.txt", "a+") as f: 
            f.write("Internal event: system time " + datetime.now().strftime("%H:%M:%S%f") + ", logical clock time " + str(self.logical_clock) + "\n")

    # Main loop that simulates each clock cycle of the machine
    def run(self): 
        while True: 
            start_time = time.time()
            if not self.read_message(): 
                val = random.randint(1, 10) 
                if val == 1 or val == 2: 
                    self.write_message(self.config[val + 1])
                elif val == 3: 
                    for port in self.config[2:]: 
                        self.write_message(port) 
                else:
                    self.internal_event()
            time.sleep(1 / self.tick - (time.time() - start_time))

if __name__ == '__main__': 
    port1, port2, port3 = 11113, 22224, 33335 # listening ports for each of the 3 machines

    # Start 3 separate machines as 3 separate processes, with the appropriate network
    # configurations of the form [host, listening port, port to connect to, port to connect to]
    config1 = ["", port1, port2, port3]
    p1 = Process(target=Machine(config1).run)
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
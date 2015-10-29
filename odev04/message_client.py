import socket
import threading


class ReadThread(threading.Thread):
    def __init__(self, thread_id):
        threading.Thread.__init__(self)
        self.thread_id = thread_id

    def run(self):
        print("Starting Thread-" + str(self.thread_id))
        read_from_server()
        print("Ending Thread-" + str(self.thread_id))


class WriteThread(threading.Thread):
    def __init__(self, thread_id):
        threading.Thread.__init__(self)
        self.thread_id = thread_id

    def run(self):
        print("Starting Thread-" + str(self.thread_id))
        write_to_server()
        print("Ending Thread-" + str(self.thread_id))


s = socket.socket()
host = "127.0.0.1"
port = 12345
s.connect((host, port))
rThread = ReadThread(1)
rThread.start()
wThread = WriteThread(2)
wThread.start()
message = ""
exitFlag = False

while not exitFlag:
    pass

rThread.join()
wThread.join()
s.close()


def read_from_server():
    while not exitFlag:
        received_msg = s.recv()
        if received_msg != "":
            print(received_msg + ", server sent")


def write_to_server():
    global message, exitFlag
    while not exitFlag:
        message = input('Enter a message to send server:')
        s.send(message)
        if message == "end":
            exitFlag = True

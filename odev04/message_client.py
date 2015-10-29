import socket
import threading

s = socket.socket()
host = "127.0.0.1"
port = 12345
message = ""
exitFlag = False


def main():
    s.connect((host, port))
    r_thread = ReadThread(1)
    r_thread.start()
    w_thread = WriteThread(2)
    w_thread.start()
    while not exitFlag:
        pass
    r_thread.join()
    w_thread.join()
    s.close()


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


def read_from_server():
    global exitFlag
    while not exitFlag:
        received_msg = s.recv(1024).decode()
        if received_msg != "":
            print(received_msg)


def write_to_server():
    global message, exitFlag
    while not exitFlag:
        message = input('Enter a message to send server:')
        s.send(bytes(message, 'UTF-8'))
        if message == "end":
            exitFlag = True


if __name__ == '__main__':
    main()

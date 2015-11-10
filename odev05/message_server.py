import threading
import queue
import socket

threadCounter = 0
s = socket.socket()
host = socket.gethostname()
port = 12345
s.bind((host, port))
s.listen(5)
thread_queue = queue.Queue()
log_queue = queue.Queue()
fihrist = {}


def main():
    global threadCounter
    while True:
        print("Waiting for connection")
        client_socket, client_addr = s.accept()
        print("Got a connection from ", client_addr)
        threadCounter += 1
        write_thread = WriteThread('write_' + str(threadCounter), client_socket, client_addr, thread_queue, log_queue)
        read_thread = ReadThread('read_' + str(threadCounter), client_socket, client_addr, thread_queue, log_queue)


class ReadThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_addr, thread_queue, log_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.thread_queue = thread_queue
        self.log_queue = log_queue
        self.nickname = ""

    def parser(self, data):
        global fihrist
        data = data.strip()
        # kodu oluşturan ilk üç hane
        code = data[0:3]
        # argüman
        argument = data[4:]
        # giriş yapılmadıysa ERL hatası ver
        if not self.nickname and code != "USR":
            response = "ERL"
        # nickname tanımlanıyor
        elif code == "USR":
            #
            if argument not in fihrist.keys():
                self.nickname = argument
                fihrist.update({self.nickname: self.client_socket})
                response = "HEL" + self.nickname
            else:
                response = "REJ" + argument
        # çıkış yapılması talebi
        elif code == "QUI":
            response = "BYE" + self.nickname
        # tic-toc bağlantı testi
        elif code == "TIC":
            response = "TOC"
        # kullanıcıları listeleme
        elif code == "LSQ":
            response = "LSA " + "".join('%s:' % k for k in fihrist.keys()).rstrip(':')
        # genel mesaj gönderme
        elif code == "SAY":
            for to_nickname in fihrist.keys():
                fihrist[to_nickname].put((self.nickname, argument))
            response = "SOK"
        # özel mesaj gönderme
        elif code == "MSG":
            to_nickname, message = argument.split(':')
            if to_nickname not in fihrist.keys():
                response = "MNO " + to_nickname
            else:
                fihrist[to_nickname].put((to_nickname, self.nickname, message))
                response = "MOK"
        # hatalı kod girildiyse ERR hatası ver
        else:
            response = "ERR"
        return response


class WriteThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_addr, thread_queue, log_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_addr = client_addr
        self.thread_queue = thread_queue
        self.log_queue = log_queue

    def run(self):
        self.log_queue.put("Starting " + self.thread_name)
        while True:
            if not self.thread_queue.empty():
                data = self.thread_queue.get()
                if len(data) > 2:
                    to_nickname, from_nickname, message = data
                    # özel mesaj gönderme
                else:
                    from_nickname, message = data
                    # genel mesaj gönderme

        self.log_queue.put("Exiting " + self.thread_name)

import threading
import queue
import socket

s = socket.socket()
host = socket.gethostname()
port = 12345
s.bind((host, port))
s.listen(5)
log_queue = queue.Queue()
fihrist = {}
threadLock = threading.Lock()


def main():
    thread_counter = 0
    while True:
        print("Waiting for connection")
        client_socket, client_address = s.accept()
        print("Got a connection from ", client_address)
        thread_counter += 1
        thread_queue = queue.Queue()
        WriteThread('WriteThread_' + str(thread_counter), client_socket, client_address, thread_queue,
                    log_queue).start()
        ReadThread('ReadThread_' + str(thread_counter), client_socket, client_address, thread_queue,
                   log_queue).start()


class ReadThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_address, thread_queue, log_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_address = client_address
        self.thread_queue = thread_queue
        self.log_queue = log_queue
        self.nickname = ""

    def run(self):
        self.log_queue.put("Starting %s" % self.thread_name)
        while True:
            received_message = self.client_socket.recv(1024).decode()
            self.client_socket.send(bytes(self.parser(received_message), 'UTF-8'))
            # client'tan QUI kodu alındığında soketi kapat
            if received_message == "QUI":
                self.client_socket.close()
                break
        self.log_queue.put("Ending %s" % self.thread_name)

    def parser(self, data):
        global fihrist, threadLock
        data = data.strip()
        # eğer data formatı bozuk ise hata ver
        if len(data) < 3 or " " in data[0:3] or (len(data) > 3 and data[3] != " "):
            return "ERR\n"

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
                fihrist.update({self.nickname: self.thread_queue})
                response = "HEL" + self.nickname
            else:
                response = "REJ" + argument
        # çıkış yapılması talebi
        elif code == "QUI":
            fihrist.pop(self.nickname)
            response = "BYE" + self.nickname
        # tic-toc bağlantı testi
        elif code == "TIC":
            response = "TOC"
        # kullanıcıları listeleme
        elif code == "LSQ":
            response = "LSA " + "".join('%s:' % k for k in fihrist.keys()).rstrip(':')
        # genel mesaj gönderme
        elif code == "SAY":
            # thread lock devreye sokuluyor
            threadLock.acquire()
            for to_nickname in fihrist.keys():
                fihrist[to_nickname].put((self.nickname, argument))
            # thread lock devre dışı bırakılıyor
            threadLock.release()
            response = "SOK"
        # özel mesaj gönderme
        elif code == "MSG":
            to_nickname, message = argument.split(':')
            if to_nickname not in fihrist.keys():
                response = "MNO " + to_nickname
            else:
                # thread lock devreye sokuluyor
                threadLock.acquire()
                fihrist[to_nickname].put((to_nickname, self.nickname, message))
                # thread lock devre dışı bırakılıyor
                threadLock.release()
                response = "MOK"
        # sistem mesajı gönderme
        elif code == "SYS":
            threadLock.acquire()
            self.thread_queue.put(argument)
            threadLock.release()
            response = "YOK"
        # hatalı kod girildiyse ERR hatası ver
        else:
            response = "ERR"
        return response + "\n"


class WriteThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_address, thread_queue, log_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_address = client_address
        self.thread_queue = thread_queue
        self.log_queue = log_queue

    def run(self):
        self.log_queue.put("Starting " + self.thread_name)
        while True:
            if not self.thread_queue.empty():
                queue_data = self.thread_queue.get()
                # özel mesaj gönderme
                if len(queue_data) > 2:
                    to_nickname, from_nickname, message = queue_data
                    message_to_send = "MSG %s" % message
                # genel mesaj gönderme
                elif len(queue_data) == 2:
                    from_nickname, message = queue_data
                    message_to_send = "SAY %s" % message
                # sistem mesajı gönderme
                else:
                    message_to_send = "SYS %s" % queue_data
                self.client_socket.send(bytes(message_to_send), 'UTF-8')

        self.log_queue.put("Exiting " + self.thread_name)

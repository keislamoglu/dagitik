import socket
import threading
import random
import datetime


class ServerThread(threading.Thread):
    def __init__(self, thread_id, client_socket, client_addr):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.client_socket = client_socket
        self.client_addr = client_addr

    def run(self):
        print("Starting Thread-" + str(self.thread_id))
        connect_to_client(self.client_socket)
        print("Ending Thread-" + str(self.thread_id))


threadCounter = 0
randomNumber = 0
s = socket.socket()
host = "0.0.0.0"
port = 12345
s.bind((host, port))
s.listen(5)


def main():
    global threadCounter
    while True:
        print("Waiting for connection")
        c, addr = s.accept()
        print('Got a connection from ', addr)
        threadCounter += 1
        thread = ServerThread(threadCounter, c, addr)
        thread.start()


def connect_to_client(client_socket):
    while True:
        # Rastgele bir zamanda ekrana "Merhaba, saat..." iletisi gönderiliyor
        global randomNumber
        if randomNumber == 0:
            time = "Merhaba, saat şu an %s" % datetime.datetime.now().strftime("%H:%M")
            client_socket.send(bytes(time, 'UTF-8'))
            randomNumber = random.randint(1000, 5000)
        randomNumber -= 1
        # İstemcinin mesajı alınıyor, eğer "end" ise soket kapatılıyor
        message = client_socket.recv(1024)
        if message == "end":
            client_socket.close()
            break


if __name__ == '__main__':
    main()

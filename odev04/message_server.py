import socket
import threading
import random
import datetime

threadCounter = 0
s = socket.socket()
host = socket.gethostname()
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


class ServerThread(threading.Thread):
    def __init__(self, thread_id, client_socket, client_addr):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.client_socket = client_socket
        self.client_addr = client_addr

    def run(self):
        print("Starting Thread-" + str(self.thread_id))
        connect_to_client(self.client_socket, self.client_addr)
        print("Ending Thread-" + str(self.thread_id))


def connect_to_client(client_socket, client_addr):
    random_number = 0
    while True:
        if random_number == 0:
            time = "Merhaba, saat şu an %s" % datetime.datetime.now().strftime("%H:%M") + '\n'
            client_socket.send(bytes(time, 'UTF-8'))
            random_number = random.randint(0, 9)  # 0-9 arasında aldığı değer adedi sonrasında gönderir
        random_number -= 1
        # İstemcinin mesajı alınıyor, eğer "end" ise soket kapatılıyor
        message = client_socket.recv(1024).decode()
        if message == "end":
            client_socket.close()
            break
        else:
            client_socket.send(bytes("Peki " + str(client_addr) + '\n', 'UTF-8'))


if __name__ == '__main__':
    main()

import threading
import queue
import socket
import time

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
    LoggerThread('LogThread', log_queue, 'log.txt')
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
        print("Starting %s" % self.thread_name)  # silinecek
        self.log_queue.put("Starting %s" % self.thread_name)
        while True:
            received_message = self.client_socket.recv(1024).decode()
            result = self.parser(received_message)
            if not result == 0:
                self.thread_queue.put('end')
                break
        print("Ending %s" % self.thread_name)  # silinecek
        self.log_queue.put("Ending %s" % self.thread_name)

    def parser(self, data):
        global fihrist, threadLock
        data = data.strip()

        # eğer data formatı bozuk ise hata ver
        if len(data) < 3 or " " in data[0:3] or (len(data) > 3 and data[3] != " "):
            self.csend("ERR\n")
            return 0

        # kodu oluşturan ilk üç hane
        code = data[0:3]
        # argüman
        argument = data[4:]

        # giriş yapılmadıysa ERL hatası ver
        if not self.nickname and code != "USR":
            response = "ERL"
        # nickname tanımlanıyor
        elif code == "USR":
            nickname = argument
            # eğer nickname zaten alınmışsa ve yenisi alınmak istiyorsa eskisi listeden çıkarılır
            if not self.nickname == "":
                fihrist[self.nickname].pop()
            # belirtilen nickname fihrist listesinde yok ise listeye eklenir
            if nickname not in fihrist.keys():
                self.nickname = nickname
                # yeni nickname fihriste ekleniyor
                fihrist.update({self.nickname: self.thread_queue})
                response = "HEL " + self.nickname
                self.log_queue.put(self.nickname + " has joined.")
            # belirtilen nickname zaten mevcut ise bağlantı reddedilir
            else:
                response = "REJ " + nickname
                # client socket'e cevap gönderiliyor
                self.csend(response)
                # socket bağlantısı kapatılıyor
                self.client_socket.close()
                return 1
        # çıkış yapılması talebi
        elif code == "QUI":
            fihrist.pop(self.nickname)
            response = "BYE " + self.nickname
            self.csend(response)
            self.client_socket.close()
            self.log_queue.put(self.nickname + " has left.")
            return 1
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

        # client socket'ine cevap gönderiliyor
        self.csend(response + "\n")
        # hatasız bir şekilde sonlandı
        return 0

    def csend(self, data):
        self.client_socket.send(bytes(data, 'UTF-8'))


class WriteThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_address, thread_queue, log_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_address = client_address
        self.thread_queue = thread_queue
        self.log_queue = log_queue

    def run(self):
        print("Starting %s" % self.thread_name)  # silinecek
        self.log_queue.put("Starting %s" % self.thread_name)
        while True:
            if not self.thread_queue.empty():
                queue_data = self.thread_queue.get()
                if queue_data == "end":
                    break
                else:
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
                    try:
                        self.csend(message_to_send)
                    except socket.error:
                        self.client_socket.close()
                        break
        print("Ending %s" % self.thread_name)  # silinecek
        self.log_queue.put("Ending %s" % self.thread_name)

    def csend(self, data):
        self.client_socket.send(bytes(data, 'UTF-8'))


class LoggerThread(threading.Thread):
    def __init__(self, thread_name, log_queue, log_file_name):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.log_queue = log_queue
        self.log_file_name = log_file_name
        self.log_file = open(log_file_name, 'a+')

    def log(self, message):
        t = time.ctime()
        self.log_file.write("%s: %s\n" % (t, message))
        self.log_file.flush()

    def run(self):
        self.log("Starting %s" % self.thread_name)
        while True:
            if not self.log_queue.emty():
                to_be_logged = self.log_queue.get()
                if to_be_logged == "end":
                    break
                else:
                    self.log(to_be_logged)
        self.log("Ending %s" % self.thread_name)
        self.log_file.close()


if __name__ == '__main__':
    main()

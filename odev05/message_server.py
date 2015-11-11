import threading
import Queue
import socket
import time

s = socket.socket()
host = socket.gethostname()
port = 12345
s.bind((host, port))
s.listen(5)
log_queue = Queue.Queue()
fihrist = {}
threadLock = threading.Lock()


def main():
    global fihrist
    thread_counter = 0
    logger_thread = LoggerThread('LogThread', log_queue, 'log.txt')
    logger_thread.start()
    while True:
        log_queue.put("Waiting for connection")
        client_socket, client_address = s.accept()
        log_queue.put("Got a connection from %s" % str(client_address))
        thread_counter += 1
        thread_queue = Queue.Queue()
        WriteThread('WriteThread_' + str(thread_counter), client_socket, client_address, thread_queue,
                    log_queue).start()
        ReadThread('ReadThread_' + str(thread_counter), client_socket, client_address, thread_queue,
                   log_queue, fihrist).start()
    log_queue.put("end")
    logger_thread.join()


class ReadThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_address, thread_queue, log_queue, fihrist):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_address = client_address
        self.thread_queue = thread_queue
        self.log_queue = log_queue
        self.nickname = ""
        self.fihrist = fihrist

    def run(self):
        self.log_queue.put("Starting %s" % self.thread_name)
        while True:
            received_message = self.client_socket.recv(1024)
            result = self.parser(received_message)
            if not result == 0:
                self.thread_queue.put('end')
                break
        self.log_queue.put("Ending %s" % self.thread_name)

    def parser(self, data):
        global threadLock
        data = data.strip()

        # eger data formati bozuk ise hata ver
        if len(data) < 3 or " " in data[0:3] or (len(data) > 3 and data[3] != " "):
            self.csend("ERR\n")
            return 0

        # kodu olusturan ilk uc hane
        code = data[0:3]
        # arguman
        argument = data[4:]

        # giris yapilmadiysa ERL hatasi ver
        if not self.nickname and code != "USR":
            response = "ERL"
        # nickname tanimlaniyor
        elif self.nickname == "" and code == "USR":
            nickname = argument
            # belirtilen nickname fihrist listesinde yok ise listeye eklenir
            if nickname not in self.fihrist.keys():
                self.nickname = nickname
                # yeni nickname fihriste ekleniyor
                self.fihrist.update({self.nickname: self.thread_queue})
                response = "HEL " + self.nickname
                self.log_queue.put(self.nickname + " has joined.")
            # belirtilen nickname zaten mevcut ise baglanti reddedilir
            else:
                response = "REJ " + nickname
        # cikis yapilmasi talebi
        elif code == "QUI":
            self.fihrist.pop(self.nickname)
            response = "BYE " + self.nickname
            self.csend(response)
            self.client_socket.close()
            self.log_queue.put(self.nickname + " has left.")
            return 1
        # tic-toc baglanti testi
        elif code == "TIC":
            response = "TOC"
        # kullanicilari listeleme
        elif code == "LSQ":
            response = "LSA " + "".join('%s:' % k for k in self.fihrist.keys()).rstrip(':')
        # genel mesaj gonderme
        elif code == "SAY":
            # thread lock devreye sokuluyor
            threadLock.acquire()
            for to_nickname in self.fihrist.keys():
                fihrist[to_nickname].put((self.nickname, argument))
            # thread lock devre disi birakiliyor
            threadLock.release()
            response = "SOK"
        # ozel mesaj gonderme
        elif code == "MSG" and ':' in argument:
            to_nickname, message = argument.split(':', 1)
            if to_nickname not in self.fihrist.keys():
                response = "MNO " + to_nickname
            else:
                # thread lock devreye sokuluyor
                threadLock.acquire()
                fihrist[to_nickname].put((to_nickname, self.nickname, message))
                # thread lock devre disi birakiliyor
                threadLock.release()
                response = "MOK"
        # sistem mesaji gonderme
        elif code == "SYS":
            threadLock.acquire()
            self.thread_queue.put(argument)
            threadLock.release()
            response = "YOK"
        # hatali kod girildiyse ERR hatasi ver
        else:
            response = "ERR"

        # client socket'ine cevap gonderiliyor
        self.csend(response + "\n")
        # hatasiz bir sekilde sonlandi
        return 0

    def csend(self, data):
        self.client_socket.send(data)


class WriteThread(threading.Thread):
    def __init__(self, thread_name, client_socket, client_address, thread_queue, log_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.client_address = client_address
        self.thread_queue = thread_queue
        self.log_queue = log_queue

    def run(self):
        self.log_queue.put("Starting %s" % self.thread_name)
        while True:
            if not self.thread_queue.empty():
                queue_data = self.thread_queue.get()
                if queue_data == "end":
                    break
                else:
                    # ozel mesaj gonderme
                    if len(queue_data) > 2:
                        to_nickname, from_nickname, message = queue_data
                        message_to_send = "MSG %s" % message
                    # genel mesaj gonderme
                    elif len(queue_data) == 2:
                        from_nickname, message = queue_data
                        message_to_send = "SAY %s" % message
                    # sistem mesaji gonderme
                    else:
                        message_to_send = "SYS %s" % queue_data
                    try:
                        self.csend(message_to_send)
                    except socket.error:
                        self.client_socket.close()
                        break
        self.log_queue.put("Ending %s" % self.thread_name)

    def csend(self, data):
        self.client_socket.send(data)


class LoggerThread(threading.Thread):
    def __init__(self, thread_name, log_queue, log_file_name):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.log_queue = log_queue
        self.log_file_name = log_file_name
        self.log_file = open(log_file_name, 'a+')

    def log(self, message):
        # thread lock devreye sokuluyor
        threadLock.acquire()
        t = time.ctime()
        self.log_file.write("%s: %s\n" % (t, message))
        self.log_file.flush()
        # thread lock devre disi birakiliyor
        threadLock.release()

    def run(self):
        self.log("Starting %s" % self.thread_name)
        while True:
            if not self.log_queue.empty():
                to_be_logged = self.log_queue.get()
                if to_be_logged == "end":
                    break
                else:
                    self.log(to_be_logged)
        self.log("Ending %s" % self.thread_name)
        self.log_file.close()


if __name__ == '__main__':
    main()

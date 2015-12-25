__author__ = 'keislamoglu'

import threading
import Queue
import socket
import re
import time

# Sabitler
TYPE_NEGOTIATOR = 'N'
TYPE_PEER = 'P'
STATE_WAITING = 'W'
STATE_SUCCESS = 'S'
STATE_NOT_RESPONDING = 'NR'
PATCH_SIZE = 128
UPDATE_INTERVAL = 600
THREADNUM = 4
QUEUENUM = 20
CONNECTION_LOST = 'CONN_LOST'
CONNECTION_CLOSED = 'CONN_CLOSED'

threadLock = threading.Lock()

s = socket.socket()
ip = socket.gethostname()
port = 34762
s.bind((ip, port))
s.listen(5)
connectPointList = {}


def main():
    while True:
        print("Waiting for connetion")
        client_socket, client_address = s.accept()
        checking_queue = Queue.Queue()
        thread_queue = Queue.Queue()
        # Client Side Thread
        ClientSideThread(checking_queue, s, client_socket, client_address, connectPointList)
        # Server Side Listener Thread
        ServerSideListenerThread(client_socket, client_address, thread_queue, checking_queue, connectPointList)
        # Server Side Sender Thread
        ServerSideSenderThread(client_socket, client_address, thread_queue, checking_queue, connectPointList)
        s.connect(client_address)


# Server Side Listener Thread
class ServerSideListenerThread(threading.Thread):
    def __init__(self, client_socket, client_address, thread_queue, checking_queue, connect_point_list):
        threading.Thread.__init__(self)
        self.checking_queue = checking_queue
        self.csocket = client_socket
        self.caddress = client_address
        self.thread_queue = thread_queue
        self.connect_point_list = connect_point_list

    def run(self):
        while True:
            received_msg = self.csocket.recv(1024)
            # socket baglantisinda hata olustugunda bos string gonderir, dolayisiyla thread'leri sonlandiririz
            if received_msg == '':
                self.put_queue(CONNECTION_LOST)
                break

            # komut ve arguman ayristiriliyor
            cmd, argument = str(received_msg).split(' ', 1)

            # komut formati dogru degilse komut hatali mesaji gonder
            if not len(cmd) == 5:
                to_queue = 'CMDER'
            # Kayit talebi
            elif cmd == 'REGME':
                connection_point = str(argument).split(':', 1)

                # ip ve port numaralari formatlari dogrulandiysa devam eder
                if is_valid_ip_port(connection_point):
                    t = time.ctime()
                    # (<ip>, <port>): (<state>, <type>, <time>) olarak node_list'e kaydediliyor
                    self.connect_point_list.update({(ip, port): (STATE_WAITING,)})
                    if self.reverse_checking():
                        t = time.time()
                        state, type = self.connect_point_list[(ip, port)]
                        self.connect_point_list.update({(ip, port): (state, type, t)})
                        to_queue = 'REGOK %s' % t
                    else:
                        to_queue = CONNECTION_CLOSED
                else:
                    to_queue = 'CMDER'

            self.put_queue(to_queue)

            # baglanti sona erdiginde thread sonlandirilir
            if to_queue == CONNECTION_CLOSED:
                break
        self.csocket.close()

    def put_queue(self, data):
        self.thread_queue.put(data)

    def reverse_checking(self):
        self.put_queue('REGWA')
        self.checking_queue.put("CHECK")
        while self.connect_point_list[(ip, port)] == STATE_WAITING:
            continue
        if self.connect_point_list[(ip, port)] == STATE_NOT_RESPONDING:
            self.put_queue('REGER')
            return False


# Server Side Sender Thread
class ServerSideSenderThread(threading.Thread):
    def __init__(self, client_socket, client_address, thread_queue, checking_queue, connect_point_list):
        threading.Thread.__init__(self)
        self.csocket = client_socket
        self.caddress = client_address
        self.thread_queue = thread_queue
        self.connect_point_list = connect_point_list

    def run(self):
        # istemci baglanir baglanmaz 'HELLO' mesaji gonderilir
        while True:
            queue_data = self.thread_queue.get()
            # kuyruktan CONNECTION_LOST veya CONNECTION_CLOSED mesaji gelirse bu iletisimin sonlandigi anlamina gelir
            if queue_data == CONNECTION_LOST or queue_data == CONNECTION_CLOSED:
                break

            if queue_data[:4] == 'REGWA':
                self.csend('REGWA')

            # kuyruktaki veri socket'e gonderilemezse socket kapatilir
            if not self.csend(queue_data):
                self.csocket.close()
                break

    def csend(self, data):
        try:
            self.csocket.send(data)
            return True
        except socket.error:
            return False


# Client Side Thread
class ClientSideThread(threading.Thread):
    def __init__(self, queue, own_socket, connect_point_list):
        threading.Thread.__init__(self)
        self.queue = queue
        self.own_socket = own_socket
        self.connect_point_list = connect_point_list

    def run(self):
        while True:
            if not self.queue.empty():
                queue_message = self.queue.get()
                if queue_message[0:5] == 'CHECK':
                    connect_point = str(queue_message[6:]).split(':')
                    self.own_socket.connect(connect_point)
                    self.own_socket.send("HELLO")
                    self.own_socket.settimeout(10.0)
                    response = self.own_socket.recv(1024)
                    if response[0:5] == 'SALUT':
                        type = response[6:1]
                        self.connect_point_list.update({connect_point: (STATE_SUCCESS, type)})
                    else:
                        self.connect_point_list.update({connect_point: (STATE_NOT_RESPONDING,)})


# --------------------
# additional functions
# --------------------

#
# <ip> ve <port>'un dogru formatta tanimlandigini kontrol eder
#
def is_valid_ip_port((ip, port)):
    # <ip>
    try:
        socket.inet_aton(ip)
    except socket.error:
        return False
    # <port>
    if not (re.match(r"\d{1,5}", port) and 0 <= int(port) <= 65535):
        return False
    # <ip> & <port> format is valid
    return True


#
# <type>'in dogru tanimlandigini kontrol eder
#
def is_valid_type(type):
    return type == TYPE_NEGOTIATOR or type == TYPE_PEER

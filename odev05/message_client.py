import sys
import threading
import Queue
import time
import socket
from PyQt4.QtCore import *
from PyQt4.QtGui import *


def main():
    client_socket = socket.socket()
    host = socket.gethostname()
    port = 12345
    client_socket.connect((host, port))
    thread_queue = Queue.Queue()
    app = ClientDialog(thread_queue)
    w_thread = WriteThread('ClientWriteThread', client_socket, thread_queue)
    w_thread.start()
    r_thread = ReadThread('ClientReadThread', client_socket, app)
    r_thread.start()
    app.run()
    r_thread.join()
    w_thread.join()
    client_socket.close()


class ReadThread(threading.Thread):
    def __init__(self, thread_name, client_socket, app):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.app = app

    def incoming_parser(self, data):
        code = data[0:3]
        argument = data[4:].rstrip("\n")
        if code == "MSG":
            from_nickname, message = argument.split(':', 1)
            # ozel mesajlar icin <<from_nickname>> formati kullanilacak
            self.app.cprint("<<%s>>: %s" % (from_nickname, message))
        elif code == "SAY":
            from_nickname, message = argument.split(':', 1)
            # genel mesajlar icin <from_nickname> formati kullanilacak
            self.app.cprint("<%s>: %s" % (from_nickname, message))
        elif code == "LSA":
            self.app.cprint("-Server-: Online users => %s" % str(argument).replace(':', ', '))
        elif code == "BYE":
            self.app.close()
            self.client_socket.close()
            return 1
        elif code == "ERL":
            self.app.cprint("-Server-: Nick not registered")
        elif code == "HEL":
            self.app.cprint("-Server-: Registered as <%s>" % argument)
        elif code == "REJ":
            self.app.cprint("-Server-: <%s> already registered" % argument)
        elif code == "ERR":
            self.app.cprint("-Server-: Error")
        elif code == "MNO":
            self.app.cprint("-Server-: User <%s> not found" % argument)

    def run(self):
        print("Read Thread has started")
        while True:
            try:
                received_message = self.client_socket.recv(1024)
                if received_message == "":
                    break
                result = self.incoming_parser(received_message)
                if result == 1:
                    break
            except socket.error:
                self.client_socket.close()
                break
        print("Read Thread has ended")


class WriteThread(threading.Thread):
    def __init__(self, thread_name, client_socket, thread_queue):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.client_socket = client_socket
        self.thread_queue = thread_queue

    def run(self):
        print("Write Thread has started")
        while True:
            if not self.thread_queue.empty():
                to_send_message = self.thread_queue.get()
                try:
                    self.client_socket.send(to_send_message)
                    if to_send_message == "QUI":
                        break
                except socket.error:
                    self.client_socket.close()
                    break
        print("Write Thread has ended")


class ClientDialog(QDialog):
    def __init__(self, thread_queue):
        self.thread_queue = thread_queue
        self.qt_app = QApplication(sys.argv)
        # Call the parent constructor on the current object
        QDialog.__init__(self, None)
        # set up the window
        self.setWindowTitle('IRC Client')
        self.setMinimumSize(500, 200)
        # Add a vertical layout
        self.vbox = QVBoxLayout()
        # The sender textbox
        self.sender = QLineEdit("", self)
        # The channel region
        self.channel = QTextBrowser()
        # The send button
        self.send_button = QPushButton('&Send')
        # Connect the Go button to its callback
        self.send_button.clicked.connect(self.outgoing_parser)
        # Add the controls to the vertical layout
        self.vbox.addWidget(self.channel)
        self.vbox.addWidget(self.sender)
        self.vbox.addWidget(self.send_button)
        # A very stretchy spacer to force the button to the bottom
        # self.vbox.addStretch(100)
        # Use the vertical layout for the current window
        self.setLayout(self.vbox)

    def outgoing_parser(self):
        data = self.sender.text()
        self.cprint("-Local-: %s" % data)
        if len(data) == 0:
            return
        to_send_message = ''
        if data[0] == '/':
            if ' ' in data:
                code, argument = str(data[1:]).split(' ', 1)
            else:
                code = data[1:]
            if code == "list":
                to_send_message = "LSQ"
            elif code == "quit":
                to_send_message = "QUI"
            elif code == "msg":
                to_nickname, message = argument.split(' ')
                to_send_message = "MSG %s:%s" % (to_nickname, message)
            elif code == "nick":
                to_send_message = "USR %s" % (argument)
            else:
                self.cprint("Local: Command Error.")
        else:
            to_send_message = "SAY %s" % data
        if not to_send_message == '':
            self.thread_queue.put(to_send_message)
        self.sender.clear()

    def cprint(self, data):
        self.channel.append(data)

    def run(self):
        self.show()
        self.qt_app.exec_()


if __name__ == '__main__':
    main()

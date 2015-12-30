from pyGraphics_ui import Ui_ImageProcessor
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys
import threading
import Queue
import numpy as np
import time
import math
import socket
import re
import json

# Sabitler
TYPE_NEGOTIATOR = 'N'
TYPE_PEER = 'P'
STATE_WAITING = 'W'
STATE_SUCCESS = 'S'
PATCH_SIZE = 128
UPDATE_INTERVAL = 600
THREADNUM = 4
QUEUENUM = 20
CONNECTION_LOST = 'CONN_LOST'
CONNECTION_CLOSED = 'CONN_CLOSED'

# Mevcut fonksiyonlarin listesi
funlist = {
    'GrayScale': (0, 255),
    'SobelFilter': (0, 255)
}
s = socket.socket()
ip = socket.gethostname()
port = 9090
s.bind((ip, port))
s.listen(5)
connectPointList = {}


class Server(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.socket = socket

    def run(self):
        threads = []
        i = 0
        while True:
            i += 1
            client_socket, client_address = self.socket.accept()
            server_queue = Queue.Queue()
            checking_queue = Queue.Queue()
            server_listener = ServerSideListenerThread("server_listener_%d" % i, checking_queue, server_queue,
                                                       client_socket, client_address,
                                                       connectPointList)
            server_sender = ServerSideSenderThread("server_sender_%d" % i, server_queue, client_socket, client_address)
            checker = CheckerThread("checker_%d" % i, checking_queue, socket, connectPointList)
            threads.append(server_listener)
            threads.append(server_sender)
            threads.append(checker)

        for t in threads:
            t.join()


class ServerSideListenerThread(threading.Thread):
    def __init__(self, name, checking_queue, server_queue, client_socket, client_address, connect_point_list):
        threading.Thread.__init__(self)
        self.name = name
        self.csocket = client_socket
        self.caddress = client_address
        self.server_queue = server_queue
        self.connect_point_list = connect_point_list
        self.checking_queue = checking_queue
        self.__connect_point = False

    def run(self):
        while True:
            received_msg = self.csocket.recv(1024)
            if received_msg == '':
                self.put_queue(CONNECTION_LOST)
                break
            if len(str(received_msg).split(' ', 1)) == 2:
                cmd, argument = str(received_msg).split(' ', 1)
            else:
                cmd = received_msg
                argument = False

            if not len(cmd) == 5:
                to_queue = 'CMDER'

            elif cmd != 'REGME' and cmd != 'HELLO' and (
                        not self.__connect_point or get_node_status(self.__connect_point) != STATE_SUCCESS):
                to_queue = 'REGER'
            elif cmd == 'HELLO':
                to_queue = 'SALUT %s' % TYPE_NEGOTIATOR
            elif cmd == 'CLOSE':
                self.connect_point_list.pop(self.__connect_point)
                to_queue = 'BUBYE'
            # Kayit talebi
            elif cmd == 'REGME':
                self.__connect_point = str(argument).split(':', 1)
                # ip ve port numaralari formatlari dogrulandiysa devam eder
                if is_valid_ip_port(self.__connect_point):
                    if not node_exists(self.__connect_point) or not get_node_status(
                            self.__connect_point) == STATE_SUCCESS:
                        # (<ip>, <port>): (<state>, <time>, <type>) olarak node_list'e kaydediliyor
                        self.connect_point_list.update({self.__connect_point: (STATE_WAITING,)})
                        to_queue = 'REGWA'
                        self.reverse_checking()
                    else:
                        t = time.time()
                        self.connect_point_list.update({self.__connect_point: (
                            get_node_status(self.__connect_point), t, get_node_type(self.__connect_point))})
                        to_queue = 'REGOK %s' % t
                else:
                    to_queue = CONNECTION_CLOSED
            elif cmd == 'GETNL':
                if argument:
                    to_queue = prepare_node_list(argument)
                else:
                    to_queue = prepare_node_list()
            elif cmd == 'FUNRQ':
                if funlist.has_key(argument):
                    to_queue = 'FUNYS %s:%s' % (argument, json.dumps(funlist[argument]))
                else:
                    to_queue = 'FUNNO %s' % argument
            else:
                to_queue = 'CMDER'

            self.put_queue(to_queue)
            # baglanti sona erdiginde thread sonlandirilir
            if to_queue == CONNECTION_CLOSED:
                break
        self.csocket.close()

    def put_queue(self, data):
        self.server_queue.put(data)

    def reverse_checking(self):
        self.checking_queue.put("CHECK %s:%s" % self.__connect_point)


class ServerSideSenderThread(threading.Thread):
    def __init__(self, name, server_queue, client_socket, client_address):
        threading.Thread.__init__(self)
        self.name = name
        self.server_queue = server_queue
        self.csocket = client_socket
        self.caddress = client_address

    def run(self):
        # istemci baglanir baglanmaz 'HELLO' mesaji gonderilir
        while True:
            queue_data = self.server_queue.get()
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


# Checker Thread
class CheckerThread(threading.Thread):
    def __init__(self, name, checking_queue, own_socket, connect_point_list):
        threading.Thread.__init__(self)
        self.name = name
        self.checking_queue = checking_queue
        self.own_socket = own_socket
        self.connect_point_list = connect_point_list

    def run(self):
        while True:
            if not self.checking_queue.empty():
                queue_message = self.checking_queue.get()
                if queue_message[0:5] == 'CHECK':
                    connect_point = str(queue_message[6:]).split(':')
                    try:
                        self.own_socket.connect(connect_point)
                        self.own_socket.send('HELLO')
                        response = self.own_socket.recv(1024)
                        # SALUT cevabi ve type gonderildiginde connect_point_list'te guncellenir
                        if response[0:5] == 'SALUT' and is_valid_type(response[6:1]):
                            self.connect_point_list.update({connect_point: (STATE_SUCCESS, time.time(), response[6:1])})
                    except socket.error:
                        self.connect_point_list.pop(connect_point)


class ClientSideListenerThread(threading.Thread):
    def __init__(self, client_queue, server_socket, server_address, connect_point_list):
        threading.Thread.__init__(self)
        self.client_queue = client_queue
        self.ssocket = server_socket
        self.saddress = server_address
        self.connect_point_list = connect_point_list

    def run(self):
        while True:
            received_msg = self.ssocket.recv(1024)
            if received_msg == '':
                self.put_queue(CONNECTION_LOST)
                break

    def put_queue(self, data):
        self.client_queue.put(data)


class ClientSideSenderThread(threading.Thread):
    def __init__(self, client_queue, server_socket, server_address, connect_point_list):
        threading.Thread.__init__(self)
        self.client_queue = client_queue
        self.connect_point_list = connect_point_list
        self.__connect_point = False
        self.ssocket = server_socket
        self.saddress = server_address

    def run(self):
        while True:
            if not self.client_queue.empty():
                queue_message = self.client_queue.get()
                if queue_message == CONNECTION_LOST or queue_message == CONNECTION_CLOSED:
                    break

    def ssend(self, data):
        try:
            self.ssocket.send(data)
            return True
        except socket.error:
            return False


def rgb2gray(rgbint):
    # convert the 32 bit color into 8-bit grayscale
    b = rgbint & 255
    g = (rgbint >> 8) & 255
    r = (rgbint >> 16) & 255
    return (r + g + b) // 3


def gray2rgb(gray):
    # convert the 8bit ro 32bit (of course the color info is lost)
    return gray * 65536 + gray * 256 + gray


class WorkerThread(threading.Thread):
    def __init__(self, name, inQueue, outQueue, pLock):
        threading.Thread.__init__(self)
        self.name = name
        self.inQueue = inQueue  # the queue to read unprocessed data
        self.outQueue = outQueue  # the queue to put processed data
        self.pLock = pLock
        self.patchsize = 128

    def convertGray(self, header, patch):
        # convert the patch to gray (actually does nothing as the incoming
        # data is already 8bit grayscale data)
        newMessage = [0] * self.patchsize * self.patchsize
        for i in range(0, self.patchsize * self.patchsize):
            newMessage[i] = patch[i]
        return (header, newMessage)

    def filterSobel(self, header, patch, threshold):
        # convolve the patch with the matrix [[1,0,-1],[2,0,-2][1,0,-1]]
        # read how the convolution is applied in discrete domain
        newMessage = [0] * self.patchsize * self.patchsize
        for i in range(1, self.patchsize - 1):
            for j in range(1, self.patchsize - 1):
                index0 = j * self.patchsize + i  # top line index
                index1 = (j + 1) * self.patchsize + i  # same line index
                index1r = (j - 1) * self.patchsize + i  # bottom line index
                temp0 = \
                    + 1 * patch[index1r - 1] \
                    - 1 * patch[index1r + 1] \
                    + 2 * patch[index0 - 1] \
                    - 2 * patch[index0 + 1] \
                    + 1 * patch[index1 - 1] \
                    - 1 * patch[index1 + 1]

                temp1 = \
                    - 1 * patch[index1r - 1] \
                    - 2 * patch[index1r] \
                    - 1 * patch[index1r + 1] \
                    + 1 * patch[index1 - 1] \
                    + 2 * patch[index1] \
                    + 1 * patch[index1 + 1]

                newMessage[index0] = int(math.sqrt(temp0 ** 2 + temp1 ** 2))
                # apply the threshold parameter
                # if newMessage[index0] > threshold:
                #     newMessage[index0] = 255
                # else:
                #     newMessage[index0] = 0
        return (header, newMessage)

    def run(self):
        print self.name + ": Starting."
        while (True):
            if self.inQueue.qsize() > 0:
                message = self.inQueue.get()
                if message == "END":
                    print self.name + ": Ending."
                    break
                print self.name + ": " + str(message[0][0]) + \
                      " " + str(message[0][1]) + " Queue size: " \
                      + str(self.inQueue.qsize())
                if str(message[0][0]) == "SobelFilter":
                    outMessage = self.filterSobel(message[0][1], message[1],
                                                  128)
                if str(message[0][0]) == "GrayScale":
                    outMessage = self.convertGray(message[0][1], message[1])
                # self.pLock.acquire()
                self.outQueue.put(outMessage)
                # self.pLock.release()
            time.sleep(.01)


class imGui(QMainWindow):
    def __init__(self, workQueue, processedQueue, pLock):
        self.qt_app = QApplication(sys.argv)
        QWidget.__init__(self, None)

        # create the main ui
        self.pQueue = processedQueue
        self.wQueue = workQueue
        self.ui = Ui_ImageProcessor()
        self.ui.setupUi(self)
        self.imageScene = QGraphicsScene()
        self.original = None
        self.processed = None
        self.frameScaled = None
        self.imageFile = None
        self.pLock = pLock
        self.patchsize = 128

        # fill combobox
        self.ui.boxFunction.addItem("GrayScale")
        self.ui.boxFunction.addItem("SobelFilter")

        # connect buttons
        self.ui.buttonLoadImage.clicked.connect(self.loadImagePressed)
        self.ui.buttonResetImage.clicked.connect(self.resetImagePressed)
        self.ui.buttonStartProcess.clicked.connect(self.startProcess)
        self.ui.buttonStopProcess.clicked.connect(self.stopProcess)

        # start timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.collectPatch)
        self.timer.start(10)

        self.sTimer = QTimer()
        self.sTimer.timeout.connect(self.scheduler)

        self.perms = None

        self.sceneObject = None

    def loadImagePressed(self):
        # load the image from a file into a QImage object
        imageFile = QFileDialog.getOpenFileName(self,
                                                'Open file',
                                                '.',
                                                'Images (*.png *.xpm '
                                                '*.jpg)')
        if not imageFile:
            return
        with open(imageFile, 'r') as f:
            try:
                self.imageFile = imageFile
                self.original = QImage(imageFile)
                # say that an image is loaded
                print "Image loaded: " + imageFile
            except:
                print "Problem with image file: " + self.imageFile
                self.imageFile = None
            finally:
                self.processed = self.original.convertToFormat(
                        QImage.Format_RGB16)
                if self.imageFile:
                    # find the horizontal and vertical patch numgers
                    self.tmpPatchNum = (
                        self.processed.size().width() / self.patchsize,
                        self.processed.size().height() / self.patchsize)
                    self.numPatches = self.tmpPatchNum[0] * \
                                      self.tmpPatchNum[1]

                self.updateImage()

    def resetImagePressed(self):
        # return to the original image
        if not self.imageFile:
            return
        self.processed = self.original
        self.updateImage()

    def updateImage(self):
        # update the visual of the image with the new processed image
        if self.processed:
            multiplierh = float(self.processed.size().height()) / float(self.ui.imageView.size().height())
            multiplierw = float(self.processed.size().width()) / float(self.ui.imageView.size().width())
            if multiplierh > multiplierw:
                self.frameScaled = self.processed.scaledToHeight(self.ui.imageView.size().height() - 5)
            else:
                self.frameScaled = self.processed.scaledToWidth(self.ui.imageView.size().width() - 5)

            if self.sceneObject:
                self.imageScene.removeItem(self.sceneObject)
            self.sceneObject = self.imageScene.addPixmap(QPixmap.fromImage(self.frameScaled))
            self.imageScene.update()
            self.ui.imageView.setScene(self.imageScene)

    def serializePatch(self, x, y, offset=0):
        # serializes the patch and prepares the message data
        tempVector = [0] * (self.patchsize ** 2)
        rect = (x * self.patchsize, y * self.patchsize)
        rng = range(0, self.patchsize)

        for j in rng:
            Y = j + rect[1]
            for i in rng:
                X = i + rect[0]
                # the message contains 8-bit grayscale (0-255) data
                tempVector[j * self.patchsize + i] = \
                    rgb2gray(self.processed.pixel(X, Y))
                # we should also send the reference rectangle information
                # where to put the patch when we receive the processed
        return rect, tempVector

    def deserializePatch(self, refPix, data):
        # convert the message data into the matrix and put directy on the
        # image using the reference pixels (refPix)
        counter = 0
        for color in data:
            x = counter % self.patchsize
            y = counter // self.patchsize
            self.processed.setPixel(refPix[0] + x,
                                    refPix[1] + y,
                                    gray2rgb(color))
            counter += 1

    def scheduler(self):
        # puts the serialized patches into the work queue
        if self.processed:
            function = self.ui.boxFunction.currentText()
            if len(self.perms) > 0:
                p = self.perms.pop()
                x = p % self.tmpPatchNum[0]
                y = p // self.tmpPatchNum[0]
                rect, tempVector = self.serializePatch(x, y)
                self.wQueue.put(((function, rect), tempVector))
            else:
                self.sTimer.stop()

    def collectPatch(self):
        # collects the processed patches from the process queue
        if self.pQueue.qsize() > 0:
            for i in range(0, self.pQueue.qsize()):
                # self.pLock.acquire()
                message = self.pQueue.get()
                # self.pLock.release()
                self.deserializePatch(message[0], message[1])
            self.updateImage()

    def startProcess(self):
        # randomly organizes the patches
        self.perms = list(np.random.permutation(self.numPatches))

        # or simply orders the patches
        # self.perms = range(0,self.numPatches)
        # self.perms.reverse()

        # start scheduler's timer
        self.sTimer.start()

    def stopProcess(self):
        # stops the timer and thus the processing
        self.sTimer.stop()

    def run(self):
        self.show()
        self.qt_app.exec_()


def main():
    # the queue should contain no more than maxSize elements
    numThreads = 4
    maxSize = numThreads * 25
    workThreads = []
    workQueue = Queue.Queue()
    processedQueue = Queue.Queue(maxSize)
    pLock = threading.Lock()

    for i in range(0, numThreads):
        workThreads.append(WorkerThread("WorkerThread" + str(i),
                                        workQueue,
                                        processedQueue,
                                        pLock))
        workThreads[i].start()

    app = imGui(workQueue, processedQueue, pLock)
    app.run()

    for a in range(0, numThreads):
        workQueue.put("END")

    for thread in workThreads:
        thread.join()


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


#
# connect_point_list'i string bir protokol ifadesine donusturur
#
def prepare_node_list(nlsize=-1):
    cpl = connectPointList
    cpl_str = 'NLIST BEGIN\n'
    for cp in cpl:
        if cpl[cp][0] == STATE_SUCCESS:
            cpl_str += '%s:%s\n' % (':'.join(cp), ':'.join((cpl[cp][1], cpl[cp][2])))
        nlsize -= 1
        if nlsize == 0:
            break
    cpl_str += 'NLIST END'
    return cpl_str


#
# connect_point parametresi ile node un mevcut olup olmadigi sorgulanir
#
def get_node_status(connect_point):
    return connectPointList[connect_point][0]


#
# connect_point parametresi ile node un time degeri sorgulanir
#
def get_node_time(connect_point):
    return connectPointList[connect_point][1]


#
# connect_point parametresi ile node un type degeri sorgulanir
#
def get_node_type(connect_point):
    return connectPointList[connect_point][2]


#
# connect_point parametresi ile node un var olup olmadigi sorgulanir
#
def node_exists(connect_point):
    return connectPointList.has_key(connect_point)


if __name__ == '__main__':
    main()

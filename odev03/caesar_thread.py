import threading
from queue import Queue

exit_flag = False
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
encryption_key = 0
thread_lock = threading.Lock()
text_filename = 'metin.txt'
w_queue = Queue()


def main():
    caesar_chipper(3, 4, 5)


# Caesar Chipper func.

def caesar_chipper(s, n, l):
    global exit_flag, encrypted_file, encryption_key
    encryption_key = s
    text_file = open(text_filename, 'r')
    encrypted_file = open('crypted_%d_%d_%d.txt' % (s, n, l), 'w+')
    threads = []
    for i in range(1, n + 1):
        threads.append(CaesarChipperThread(i, 'Thread-' + str(i)))
        threads[-1].start()
    while True:
        string = text_file.read(l)
        if string == '':
            break
        w_queue.put(string)
    while not w_queue.empty():
        pass
    exit_flag = True
    for t in threads:
        t.join()
    text_file.close()
    encrypted_file.close()


# Thread class

class CaesarChipperThread(threading.Thread):
    def __init__(self, thread_id, thread_name):
        threading.Thread.__init__(self)
        # Thread ID
        self.thread_id = thread_id
        # Thread ismi
        self.name = thread_name

    def run(self):
        print('Starting %s' % self.name)
        process()
        print('Exiting %s' % self.name)


# Her bir thread'in yapacağı iş

def process():
    while not exit_flag:
        thread_lock.acquire()
        if not w_queue.empty():
            data = w_queue.get()
            if data == '':
                break
            encrypted_file.write(encrypt_string(data))
        thread_lock.release()


# Şifreleme fonksiyonu
def encrypt_string(string):
    string = string.upper()
    encrypted_string = ''
    for index, char in enumerate(string):
        if alphabet.find(char) == -1:
            encrypted_string += char
        else:
            encrypted_string += alphabet[alphabet.index(char) - encryption_key]
    return encrypted_string


if __name__ == '__main__':
    main()

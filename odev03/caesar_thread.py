import threading
from queue import Queue

exit_flag = False
alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
shifted_alphabet = ''
thread_lock = threading.Lock()
text_file = open('metin.txt', 'r')
w_queue = Queue()


def main():
    caesar_chipper(3, 4, 5)


# Caesar Chipper func.

def caesar_chipper(s, n, l):
    global text_file, exit_flag, w_queue
    shift_right_alphabet(s)
    encrypted_file = open('crypted_%d_%d_%d.txt' % (s, n, l), 'w+')
    threads = []
    for i in range(1, n + 1):
        threads.append(CaesarChipperThread(i, 'Thread-' + str(i), encrypted_file))
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


# Thread class

class CaesarChipperThread(threading.Thread):
    def __init__(self, thread_id, thread_name, encrypted_file):
        threading.Thread.__init__(self)
        # Thread ID
        self.thread_id = thread_id
        # Thread ismi
        self.name = thread_name
        # Şifreli içeriğe sahip dosya
        self.__encrypted_file = encrypted_file
        # Thread Loc
        self.__thread_lock = thread_lock

    def run(self):
        print('Starting %s' % self.name)
        process(self.__encrypted_file)
        print('Exiting %s' % self.name)

# Her bir thread'in yapacağı iş

def process(encrypted_file):
    global w_queue
    while not exit_flag:
        thread_lock.acquire()
        if not w_queue.empty():
            data = w_queue.get()
            if data == '':
                break
            encrypted_file.write(encrypt_string(data))
        thread_lock.release()


# Şifreleme yapar

def encrypt_string(string):
    string = string.upper()
    encrypted_string = ''
    for index, char in enumerate(string):
        encrypted_string += get_shifted_char(char)
    return encrypted_string


# Alfabeyi tanımlanan anahtar değeri kadar kaydırır

def shift_right_alphabet(key):
    global alphabet, shifted_alphabet
    new_alphabet = ''
    length = len(alphabet)
    for i in range(0, length):
        new_alphabet += alphabet[(i - key) % length]
    shifted_alphabet = new_alphabet


# Parametre olarak verilen karakterin kaydırma yapılmış alfabe dizisindeki karşılığını döndürür

def get_shifted_char(char):
    global shifted_alphabet, alphabet
    # Alfabede yer almıyorsa kendisini döndürür

    if alphabet.find(char) == -1:
        return char

    # Alfabade var ise kaydırılmış alfabedeki karşılığını döndürür

    else:
        return shifted_alphabet[alphabet.index(char)]


if __name__ == '__main__':
    main()

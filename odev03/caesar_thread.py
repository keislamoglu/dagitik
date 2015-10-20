import threading


# thread class
class CaesarChipperThread(threading.Thread):
    # normal düzendeki alfabe, öteleme için kullanılacak
    __alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    # ötelenmiş alfabe
    __shifted_alphabet = ''
    # şifrelenecek string
    __string = ''
    # şifrelenmiş string
    __encrypted_string = ''

    # construct
    def __init__(self, thread_id, thread_name, key, string):
        threading.Thread.__init__(self)
        # thread id
        self.thread_id = thread_id
        # thread ismi
        self.name = thread_name
        # şifrelenecek string
        self.__string = string
        # anahtar
        self.__key = key
        # alfabe sağa kaydırılıyor
        self.__shift_right_alphabet()

    # override threading run method
    def run(self):
        self.__encrypted_string = self.__encrypt_string(self.__string)

    def get_encrypted_string(self):
        return self.__encrypted_string

    # şifreleme yapan method
    def __encrypt_string(self, text):
        text = text.upper()
        encrypted_text = ''
        for index, char in enumerate(text):
            encrypted_text += self.__get_shifted_char(char)
        return encrypted_text

    # öteleme yapan method
    def __shift_right_alphabet(self):
        self.__shifted_alphabet = ''
        length = len(self.__alphabet)
        for i in range(0, length):
            self.__shifted_alphabet += self.__alphabet[(i - self.__key) % length]

    # parametre olarak verilen karakterin ötelenmiş alfabe dizisindeki karşılığını döndürür
    def __get_shifted_char(self, char):
        if self.__alphabet.find(char) == -1:
            return char
        return self.__shifted_alphabet[self.__alphabet.index(char)]


sample_text = 'lorem ipsum dolor sit amet'


def caesar_chipper(s, n, l):
    encrypted_text = ''
    length = n * l
    start_index = 0
    while len(encrypted_text) < len(sample_text):
        threads = []
        thread_start_index = start_index
        for i in range(1, n + 1):
            # bir thread için belirlenmiş olan string parçası
            thread_string_part = sample_text[thread_start_index:thread_start_index + l]
            # thread, threads listesine ekleniyor
            threads.append(
                CaesarChipperThread(i, 'Thread-' + str(i), s, thread_string_part))
            thread_start_index += l
            # son eklenen thread koşturuluyor
            threads[-1].start()
        # threadler bekleniyor
        for t in threads:
            t.join()
            # threadlerin şifrelediği kısımlar sırasıyla ekleniyor
            encrypted_text += t.get_encrypted_string()
        start_index += length
    print(encrypted_text)


caesar_chipper(0, 2, 3)

import threading


class CaesarChipperThread(threading.Thread):
    # normal düzendeki alfabe, öteleme için kullanılacak
    __alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    # ötelenmiş alfabe
    __shifted_alphabet = ''
    # şifrelenecek string
    __string = ''

    # construct
    def __init__(self, thread_id, thread_name, string, key, length_per_iteration):
        threading.Thread.__init__(self)
        # thread id
        self.thread_id = thread_id
        # thread ismi
        self.name = thread_name
        # şifrelenecek string
        self.__string = string
        # iterasyon başına düşen string uzunluğu
        self.__length_per_iteration = length_per_iteration
        # anahtar
        self.__key = key
        # alfabe sağa kaydırılıyor
        self.__shift_right_alphabet()

    # override threading run method
    def run(self):
        start_index = 0
        end_index = self.__length_per_iteration
        encrypted_string = ''
        while len(encrypted_string) < len(self.__string):
            encrypted_string += self.__encrypt_text(self.__string[start_index:end_index])
            start_index = end_index
            end_index += self.__length_per_iteration
        return encrypted_string

    # şifreleme yapan method
    def __encrypt_text(self, text):
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
        return self.__shifted_alphabet[self.__alphabet.index(char)]

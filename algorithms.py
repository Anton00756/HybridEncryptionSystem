import math
import base64


def left_shift(x: int, n: int) -> int:
    return (x << n & (2 ** x.bit_length() - 1)) | (x >> (x.bit_length() - n))


def right_shift(x: int, n: int) -> int:
    return (x >> n) | ((x & (2 ** n - 1)) << (x.bit_length() - n))


class RC6:
    def __init__(self, w: int = 32, r: int = 20, b: int = 16):
        """
        :param w: длина одного слова из 4-х [16, 32, 64]
        :param r: число раундов [0..255]
        :param b: длина ключа в байтах [0..255]
        """
        self.__block_length = w if w in {16, 32, 64} else 32
        self.__rounds = max(min(255, r), 0)
        self.__key_length = max(min(255, b - b % 8), 0)
        self.__keys = None

    def key_extension(self, key: bytes) -> None:
        if len(key) != self.__key_length:
            raise ValueError("Длина ключа не соответствует заявленной!")

        p = {16: 0xb7e1, 32: 0xb7e15163, 64: 0xb7e151628aed2a6b}.get(self.__block_length)
        q = {16: 0x9e37, 32: 0x9e3779b9, 64: 0x9e3779b97f4a7c15}.get(self.__block_length)

        word_byte_length = self.__block_length // 8
        if self.__key_length % word_byte_length:
            key = b'\x00' * (word_byte_length - (self.__key_length % word_byte_length)) + key
        words = [key[i: i + word_byte_length] for i in range(0, len(key), word_byte_length)] if self.__key_length else \
            [0]

        self.__keys = [p]
        for i in range(1, 2 * (self.__rounds + 1)):
            self.__keys.append(self.__keys[-1] + q)

        double_rounds = 2 * (self.__rounds + 1)
        g = h = i = j = 0
        for runner in range(3 * max(len(words), double_rounds)):
            g = self.__keys[i] = (self.__keys[i] + g + h) << 3
            h = self.__keys[j] = (int.from_bytes(words[j], byteorder='big') + g + h) << (g + h)
            i = (j + 1) % double_rounds
            j = (j + 1) % len(words)

        # for i in range(len(words)):
        #     words[i] = int.from_bytes(key[i:i + word_byte_length], 'big')


        # # Формирование раундового ключа
        # self.__keys = [p]  # Раундовый ключ длиной в 2r+4
        # c = int(8 * self.__key_length / self.__block_length)  # число слов в ключе
        # # Преобразование ключа в массив из с слов
        # words = []
        # for i in range(c):
        #     words.append(int("0b" + Key_bit[i:i + w], 2))
        # for i in range(2 * self.__rounds + 4 - 1):  # Инициализация массива раундовых ключей
        #     self.__keys.append((self.__keys[-1] + q) % (2 ** self.__block_length))

        # self.__keys = []
        # for i in range(self.__key_length - 1, -1, -1):
        #     self.__keys.append()
        '''
        c = [max(b, 1) / u]
for b - 1 downto 0 do
	L[i/u] = (L[i/u]<<<8) + K[i]
	
	На этом этапе нужно скопировать секретный ключ из массиваK[0...b-1]
	в массив L[0...c-1], который состоит из c=b/u слов, где u=w/8-количество байт в слове. 
	Если   b не кратен w / 8, то Lдополняется нулевыми битами до ближайшего большего кратного:
        '''

import math
import base64


def left_shift(x: int, n: int, length: int) -> int:
    n = n % length
    return (x << n & (2 ** length - 1)) | (x >> (length - n))


def right_shift(x: int, n: int, length: int) -> int:
    n = n % length
    return (x >> n) | ((x & (2 ** n - 1)) << (length - n))


class RC6:
    def __init__(self, w: int = 32, r: int = 20, b: int = 16):
        """
        :param w: длина одного слова из 4-х [16, 32, 64]
        :param r: число раундов [0..255]
        :param b: длина ключа в байтах [0..255]
        """
        self.__block_length = w if w in {16, 32, 64} else 32
        self.__block_count = self.__block_length >> 1
        self.__block_size = self.__block_count >> 2
        self.__mod_value = 2 ** self.__block_length - 1
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
        words = [int.from_bytes(key[i: i + word_byte_length], byteorder='big')
                 for i in range(0, len(key), word_byte_length)] if self.__key_length else [0]

        self.__keys = [p]
        double_rounds = 2 * (self.__rounds + 2)
        for i in range(1, double_rounds):
            self.__keys.append(self.__keys[-1] + q)

        g = h = i = j = 0
        for runner in range(3 * max(len(words), double_rounds)):
            g = self.__keys[i] = left_shift((self.__keys[i] + g + h), 3, self.__block_length)
            h = words[j] = left_shift(words[j] + g + h, g + h, self.__block_length)
            i = (j + 1) % double_rounds
            j = (j + 1) % len(words)

    def encrypt(self, data: bytes) -> bytes:
        if len(data) != self.__block_count:
            raise ValueError("Некорректная длина данных!")
        a, b, c, d = [int.from_bytes(data[i:i + self.__block_size], byteorder='big')
                      for i in range(0, self.__block_count, self.__block_size)]
        b = (b + self.__keys[0]) & self.__mod_value
        d = (d + self.__keys[1]) & self.__mod_value
        logarithm = int(math.log10(self.__block_length))
        for i in range(1, self.__rounds + 1):
            t = left_shift((b * (2 * b + 1)) & self.__mod_value, logarithm, self.__block_length)
            u = left_shift((d * (2 * d + 1)) & self.__mod_value, logarithm, self.__block_length)
            a = (left_shift(a ^ t, u, self.__block_length) + self.__keys[2 * i]) & self.__mod_value
            c = (left_shift(c ^ u, t, self.__block_length) + self.__keys[2 * i + 1]) & self.__mod_value
            a, b, c, d = b, c, d, a
        a = (a + self.__keys[-2]) & self.__mod_value
        c = (c + self.__keys[-1]) & self.__mod_value
        return a.to_bytes(self.__block_size, 'big') + b.to_bytes(self.__block_size, 'big') + \
            c.to_bytes(self.__block_size, 'big') + d.to_bytes(self.__block_size, 'big')

    def minus_modulo(self, a, b):
        return a - b & self.__mod_value

    def decrypt(self, data) -> bytes:
        if len(data) != self.__block_count:
            raise ValueError("Некорректная длина данных!")
        a, b, c, d = [int.from_bytes(data[i:i + self.__block_size], byteorder='big')
                      for i in range(0, self.__block_count, self.__block_size)]
        a = self.minus_modulo(a, self.__keys[-2])
        c = self.minus_modulo(c, self.__keys[-1])
        logarithm = int(math.log10(self.__block_length))
        for i in range(self.__rounds, 0, -1):
            a, b, c, d = d, a, b, c
            t = left_shift((b * (2 * b + 1)) & self.__mod_value, logarithm, self.__block_length)
            u = left_shift((d * (2 * d + 1)) & self.__mod_value, logarithm, self.__block_length)
            a = (right_shift(self.minus_modulo(a, self.__keys[2 * i]), u, self.__block_length) ^ t)
            c = (right_shift(self.minus_modulo(c, self.__keys[2 * i + 1]), t, self.__block_length) ^ u)
        b = self.minus_modulo(b, self.__keys[0])
        d = self.minus_modulo(d, self.__keys[1])
        return a.to_bytes(self.__block_size, 'big') + b.to_bytes(self.__block_size, 'big') + \
            c.to_bytes(self.__block_size, 'big') + d.to_bytes(self.__block_size, 'big')

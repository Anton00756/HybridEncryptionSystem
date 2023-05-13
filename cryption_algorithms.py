import copy
import math
import random
from typing import Optional, Tuple
import simplicity_tests as st


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
            g = self.__keys[i] = self.left_shift((self.__keys[i] + g + h), 3)
            h = words[j] = self.left_shift(words[j] + g + h, g + h)
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
            t = self.left_shift((b * (2 * b + 1)) & self.__mod_value, logarithm)
            u = self.left_shift((d * (2 * d + 1)) & self.__mod_value, logarithm)
            a = (self.left_shift(a ^ t, u) + self.__keys[2 * i]) & self.__mod_value
            c = (self.left_shift(c ^ u, t) + self.__keys[2 * i + 1]) & self.__mod_value
            a, b, c, d = b, c, d, a
        a = (a + self.__keys[-2]) & self.__mod_value
        c = (c + self.__keys[-1]) & self.__mod_value
        return a.to_bytes(self.__block_size, 'big') + b.to_bytes(self.__block_size, 'big') + \
            c.to_bytes(self.__block_size, 'big') + d.to_bytes(self.__block_size, 'big')

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
            t = self.left_shift((b * (2 * b + 1)) & self.__mod_value, logarithm)
            u = self.left_shift((d * (2 * d + 1)) & self.__mod_value, logarithm)
            a = (self.right_shift(self.minus_modulo(a, self.__keys[2 * i]), u) ^ t)
            c = (self.right_shift(self.minus_modulo(c, self.__keys[2 * i + 1]), t) ^ u)
        b = self.minus_modulo(b, self.__keys[0])
        d = self.minus_modulo(d, self.__keys[1])
        return a.to_bytes(self.__block_size, 'big') + b.to_bytes(self.__block_size, 'big') + \
            c.to_bytes(self.__block_size, 'big') + d.to_bytes(self.__block_size, 'big')

    def minus_modulo(self, a: int, b: int) -> int:
        return a - b & self.__mod_value

    def left_shift(self, x: int, n: int) -> int:
        n = n % self.__block_length
        return (x << n & (2 ** self.__block_length - 1)) | (x >> (self.__block_length - n))

    def right_shift(self, x: int, n: int) -> int:
        n = n % self.__block_length
        return (x >> n) | ((x & (2 ** n - 1)) << (self.__block_length - n))


class GFP2Element:
    def __init__(self, p: int, value: Optional[int] = None, params: Optional[Tuple[int, int]] = None):
        self.__p = p
        self.__a, self.__b = None, None
        if value is None:
            if params is not None:
                self.__a, self.__b = params[0] % p, params[1] % p
            else:
                self.randomize()
        else:
            self.__a = self.__b = (-value) % p

    def randomize(self) -> None:
        while True:
            self.__a = random.randint(0, self.__p - 1)
            self.__b = random.randint(0, self.__p - 1)
            if self.__a != self.__b:
                return

    def get_swapped(self) -> 'GFP2Element':
        return type(self)(self.__p, params=(self.__b, self.__a))

    def get_square(self) -> 'GFP2Element':
        return type(self)(self.__p, params=(self.__b * (self.__b - 2 * self.__a), self.__a * (self.__a - 2 * self.__b)))

    def __eq__(self, other: Optional['GFP2Element']) -> bool:
        if other is None:
            return False
        return self.__a == other.__a and self.__b == other.__b

    def is_GFP(self) -> bool:
        return self.__a == self.__b

    def __sub__(self, other) -> 'GFP2Element':
        return type(self)(self.__p, params=(self.__a - other.__a, self.__b - other.__b))

    def __add__(self, other) -> 'GFP2Element':
        return type(self)(self.__p, params=(self.__a + other.__a, self.__b + other.__b))

    @staticmethod
    def special_operation(x: 'GFP2Element', y: 'GFP2Element', z: 'GFP2Element') -> 'GFP2Element':
        return type(x)(x.__p, params=(z.__a * (y.__a - x.__b - y.__b) + z.__b * (x.__b - x.__a + y.__b),
                                      z.__a * (x.__a - x.__b + y.__a) + z.__b * (y.__b - x.__a - y.__a)))

    def __str__(self) -> str:
        return f"GPP2Element({self.__a}, {self.__b})"

    def __copy__(self) -> 'GFP2Element':
        return type(self)(self.__p, params=(self.__a, self.__b))

    def get_bytes(self, byte_length: int) -> bytes:
        """
        Получение байтового представление
        :param byte_length: Длина байтового представления одного числа
        [Лучше использовать байты для: XTR_bit_length * 3]
        :return: Байтовое представление длиной 2 * byte_length
        """
        return self.__a.to_bytes(byte_length, 'big') + self.__b.to_bytes(byte_length, 'big')


class XTR:
    def __init__(self, test_mode: st.TestMode, probability: float = 0.9, bit_length: int = 128):
        match test_mode:
            case st.TestMode.FERMAT:
                self.__test: st.SimplicityTest = st.FermatTest()
            case st.TestMode.SOLOVEY_STRASSEN:
                self.__test: st.SimplicityTest = st.SoloveyStrassenTest()
            case st.TestMode.MILLER_RABIN:
                self.__test: st.SimplicityTest = st.MillerRabinTest()
        self.__probability = probability
        self.__bit_length = bit_length
        self.public_key = None

    def generate_key(self) -> Tuple[int, int, GFP2Element]:
        while True:
            r = random.getrandbits(self.__bit_length)
            q = r ** 2 - r + 1
            if q % 12 == 7 and self.__test.check(q, self.__probability):
                break
        while True:
            k = random.getrandbits(self.__bit_length)
            p = r + k * q
            if p % 3 == 2 and self.__test.check(p, self.__probability):
                break

        quotient = (p ** 2 - p + 1) // q
        c = GFP2Element(p)
        three = GFP2Element(p, 3)
        tracer = self.Tracer(p)

        while True:
            if not tracer.calculate_tr(p + 1, c).is_GFP():
                if (tr := tracer.calculate_tr(quotient)) != three:
                    break
            c.randomize()

        self.public_key = (p, q, tr)
        return self.public_key

    def diffie_hellman(self):
        if self.public_key is None:
            self.generate_key()
        a = random.randint(2, self.public_key[1] - 3)
        tracer = self.Tracer(self.public_key[0])
        tr_g_a = tracer.calculate_tr(a, self.public_key[2])
        b = random.randint(2, self.public_key[1] - 3)
        tr_g_b = tracer.calculate_tr(b)

        k_a = tracer.calculate_tr(a, tr_g_b)
        k_b = tracer.calculate_tr(b, tr_g_a)
        print('k_1:', k_a, "\nk_2:", k_b)
        print()

    def el_gamal(self):
        if self.public_key is None:
            self.generate_key()
        tracer = self.Tracer(self.public_key[0])
        k = 23589137914
        trace_g_k = tracer.calculate_tr(k, self.public_key[2])

        b = random.randint(2, self.public_key[1] - 3)
        trace_g_b = tracer.calculate_tr(b)
        trace_g_bk = tracer.calculate_tr(b, trace_g_k)

        message = 58221519
        # print(trace_g_bk.get_bytes(self.__bit_length // 2))
        e = [pair[0] ^ pair[1] for pair in zip(message.to_bytes(self.__bit_length // 2, 'big'),
                                               trace_g_bk.get_bytes(self.__bit_length // 2))]

        decrypt_key = tracer.calculate_tr(k, trace_g_b)
        print('result:', int.from_bytes([pair[0] ^ pair[1]
                                         for pair in zip(e, decrypt_key.get_bytes(self.__bit_length // 2))], 'big'))

    class Tracer:
        def __init__(self, p: int):
            self.__p = p
            self.__c: Optional[GFP2Element] = None
            self.__c_dict: Optional[dict] = None

        def calculate_tr(self, n: int, c: Optional[GFP2Element] = None) -> GFP2Element:
            if c is not None and c != self.__c:
                self.__c = copy.copy(c)
                self.__c_dict = {0: GFP2Element(self.__p, 3), 1: self.__c}
            if self.__c is None:
                raise ValueError('Отсутствует значение "c"!')
            return self.__calculate_c(n)

        def __calculate_c(self, n: int) -> GFP2Element:
            if n in self.__c_dict:
                return self.__c_dict[n]
            current_n = 1
            for bit in map(int, bin(n)[3:]):
                new_n = (current_n << 1) | bit
                if new_n not in self.__c_dict:
                    current_c = self.__c_dict[current_n]
                    self.__c_dict[new_n] = (GFP2Element.special_operation(self.__calculate_c(current_n + 1), self.__c,
                                                                          current_c) +
                                            self.__calculate_c(current_n - 1).get_swapped()) if bit else \
                        (current_c.get_square() - (current_c + current_c).get_swapped())
                current_n = new_n
            return self.__c_dict[n]

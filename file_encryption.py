import enum
import math
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from queue import Queue

from PyQt6.QtCore import QObject, pyqtSignal

import variables
from cryption_algorithms import RC6


class AggregatorMode(enum.Enum):
    ECB = 0
    CBC = 1
    CFB = 2
    OFB = 3
    CTR = 4
    RD = 5
    RDH = 6


class ModeECB:
    def __init__(self, block_size, algorithm: RC6):
        self.__block_size = block_size
        self.__algorithm = algorithm

    def encrypt(self, data):
        with ThreadPool(processes=cpu_count()) as pool:
            return [byte for block in pool.map(self.__algorithm.encrypt,
                                               [data[i: i + self.__block_size]
                                                for i in range(0, len(data), self.__block_size)]) for byte in block]

    def decrypt(self, data):
        with ThreadPool(processes=cpu_count()) as pool:
            return [byte for block in pool.map(self.__algorithm.decrypt,
                                               [data[i: i + self.__block_size]
                                                for i in range(0, len(data), self.__block_size)]) for byte in block]


class ModeCBC:
    def __init__(self, block_size, algorithm: RC6, init):
        self.__block_size = block_size
        self.__algorithm = algorithm
        self.__previous_block = init

    def encrypt(self, data):
        result = []
        for i in range(0, len(data), self.__block_size):
            self.__previous_block = self.__algorithm.encrypt(bytes(f ^ s for f, s in
                                                                   zip(self.__previous_block,
                                                                       data[i: i + self.__block_size])))
            result.extend(self.__previous_block)
        return result

    def decrypt(self, data):
        result = []
        for i in range(0, len(data), self.__block_size):
            result.extend(list(f ^ s for f, s in zip(self.__previous_block,
                                                     self.__algorithm.decrypt(data[i: i + self.__block_size]))))
            self.__previous_block = data[i: i + self.__block_size]
        return result


class ModeCFB:
    def __init__(self, block_size, algorithm: RC6, init):
        self.__block_size = block_size
        self.__algorithm = algorithm
        self.__previous_block = init

    def encrypt(self, data):
        result = []
        for i in range(0, len(data), self.__block_size):
            self.__previous_block = bytes(f ^ s for f, s in zip(self.__algorithm.encrypt(self.__previous_block),
                                                                data[i: i + self.__block_size]))
            result.extend(self.__previous_block)
        return result

    def decrypt(self, data):
        result = []
        for i in range(0, len(data), self.__block_size):
            result.extend(list(f ^ s for f, s in zip(self.__algorithm.encrypt(self.__previous_block),
                                                     data[i: i + self.__block_size])))
            self.__previous_block = data[i: i + self.__block_size]
        return result


class ModeOFB:
    def __init__(self, block_size, algorithm: RC6, init):
        self.__block_size = block_size
        self.__algorithm = algorithm
        self.__previous_block = init

    def encrypt(self, data):
        result = []
        for i in range(0, len(data), self.__block_size):
            self.__previous_block = self.__algorithm.encrypt(self.__previous_block)
            result.extend(list(f ^ s for f, s in zip(self.__previous_block, data[i: i + self.__block_size])))
        return result

    def decrypt(self, data):
        result = []
        for i in range(0, len(data), self.__block_size):
            self.__previous_block = self.__algorithm.encrypt(self.__previous_block)
            result.extend(list(f ^ s for f, s in zip(self.__previous_block, data[i: i + self.__block_size])))
        return result


class ModeCTR:
    def __init__(self, block_size, algorithm: RC6):
        self.__block_size = block_size
        self.__algorithm = algorithm
        self.__counter = 1

    def encrypt(self, data):
        result = []
        with ThreadPool(processes=cpu_count()) as pool:
            for (index, block) in enumerate(pool.map(self.__algorithm.encrypt,
                                                     (i.to_bytes(self.__block_size, byteorder="big")
                                                      for i in range(self.__counter,
                                                                     self.__counter +
                                                                     math.ceil(len(data) / self.__block_size))))):
                pos = index * self.__block_size
                result.extend(list(f ^ s for f, s in zip(block, data[pos: pos + self.__block_size])))
        self.__counter += math.ceil(len(data) / self.__block_size)
        return result

    def decrypt(self, data):
        result = []
        with ThreadPool(processes=cpu_count()) as pool:
            for (index, block) in enumerate(pool.map(self.__algorithm.encrypt,
                                                     (i.to_bytes(self.__block_size, byteorder="big")
                                                      for i in range(self.__counter,
                                                                     self.__counter +
                                                                     math.ceil(len(data) / self.__block_size))))):
                pos = index * self.__block_size
                result.extend(list(f ^ s for f, s in zip(block, data[pos: pos + self.__block_size])))
        self.__counter += math.ceil(len(data) / self.__block_size)
        return result


class ModeRD:
    def __init__(self, block_size, algorithm: RC6, init=None):
        self.__block_size = block_size
        self.__algorithm = algorithm
        if init is not None:
            self.__init_vector = init
            self.__delta = int.from_bytes(init[len(init) // 2:], byteorder='big')
        else:
            self.__init_vector = None
            self.__delta = None
        self.__block_value = None

    def encrypt(self, data):
        result = []
        blocks = []
        if self.__block_value is None:
            self.__block_value = int.from_bytes(self.__init_vector, byteorder='big')
            blocks.append(self.__init_vector)
        blocks.extend([[a ^ b for a, b in zip(f, s)] for f, s in
                       zip((i.to_bytes(self.__block_size, byteorder='big')
                            for i in range(self.__block_value,
                                           self.__block_value + math.ceil(len(data) / self.__block_size) * self.__delta,
                                           self.__delta)),
                           (data[i: i + self.__block_size] for i in range(0, len(data), self.__block_size)))])
        with ThreadPool(processes=cpu_count()) as pool:
            for block in pool.map(self.__algorithm.encrypt, blocks):
                result.extend(block)
        self.__block_value += math.ceil(len(data) / self.__block_size) * self.__delta
        return result

    def decrypt(self, data):
        result = []
        if self.__block_value is None:
            self.__delta = int.from_bytes(self.__algorithm.decrypt(data[:self.__block_size])[self.__block_size // 2:],
                                          byteorder='big')
            self.__block_value = int.from_bytes(self.__algorithm.decrypt(data[:self.__block_size]), byteorder='big')
            data = data[self.__block_size:]
        with ThreadPool(processes=cpu_count()) as pool:
            for block in pool.map(self.__algorithm.decrypt, [data[i: i + self.__block_size]
                                                             for i in range(0, len(data), self.__block_size)]):
                result.extend(f ^ s for f, s in zip(block,
                                                    self.__block_value.to_bytes(self.__block_size, byteorder='big')))
                self.__block_value += self.__delta
        return result


class ModeRDH:
    def __init__(self, block_size, algorithm: RC6, init=None):
        self.__block_size = block_size
        self.__algorithm = algorithm
        if init is not None:
            self.__init_vector = init
            self.__delta = int.from_bytes(init[len(init) // 2:], byteorder='big')
        else:
            self.__init_vector = None
            self.__delta = None
        self.__block_value = None

    def encrypt(self, data):
        result = []
        blocks = []
        if self.__block_value is None:
            self.__block_value = int.from_bytes(self.__init_vector, byteorder='big')
            blocks.append(self.__init_vector)
            blocks.append(hash(tuple(data)).to_bytes(self.__block_size, byteorder='big', signed=True))
        blocks.extend([[a ^ b for a, b in zip(f, s)] for f, s in
                       zip((i.to_bytes(self.__block_size, byteorder='big')
                            for i in range(self.__block_value,
                                           self.__block_value + math.ceil(len(data) / self.__block_size) * self.__delta,
                                           self.__delta)),
                           (data[i: i + self.__block_size] for i in range(0, len(data), self.__block_size)))])
        with ThreadPool(processes=cpu_count()) as pool:
            for block in pool.map(self.__algorithm.encrypt, blocks):
                result.extend(block)
        self.__block_value += math.ceil(len(data) / self.__block_size) * self.__delta
        return result

    def decrypt(self, data):
        result = []
        hash_value = None
        if self.__block_value is None:
            self.__delta = int.from_bytes(self.__algorithm.decrypt(data[:self.__block_size])[self.__block_size // 2:],
                                          byteorder='big')
            self.__block_value = int.from_bytes(self.__algorithm.decrypt(data[:self.__block_size]), byteorder='big')
            hash_value = int.from_bytes(self.__algorithm.decrypt(data[self.__block_size:2 * self.__block_size]),
                                        byteorder='big', signed=True)
            data = data[2 * self.__block_size:]
        with ThreadPool(processes=cpu_count()) as pool:
            for block in pool.map(self.__algorithm.decrypt, [data[i: i + self.__block_size]
                                                             for i in range(0, len(data), self.__block_size)]):
                result.extend(f ^ s for f, s in zip(block, self.__block_value.to_bytes(self.__block_size,
                                                                                       byteorder='big')))
                self.__block_value += self.__delta
        if hash_value is not None and hash_value != hash(tuple(result)):
            raise ValueError('[RDH] Подмена данных!')
        return result


class Encrypter(QObject):
    progress = pyqtSignal(int)
    thread_queue = Queue(variables.THREAD_QUEUE_SIZE)

    def shutdown(self):
        self.__exit = True
        self.deleteLater()

    def __init__(self, algorithm: RC6, key: bytes, mode: AggregatorMode, init_vector=None, **kwargs):
        super(Encrypter, self).__init__()
        self.__algorithm = algorithm
        self.__algorithm.key_extension(key)
        self.__mode = mode
        self.__init_vector = init_vector
        self.__block_size = kwargs['block_size'] if 'block_size' in kwargs else 8
        self.__progress = 0
        self.__exit = False

    def encrypt(self, in_file: str, out_file: str):
        self.thread_queue.put(True)
        if self.__exit:
            self.thread_queue.get()
            return
        self.__progress = 0
        with (open(in_file, 'rb') as f_in,
              open(out_file, 'wb') as f_out):
            match self.__mode:
                case AggregatorMode.ECB:
                    mode_aggregator = ModeECB(self.__block_size, self.__algorithm)
                case AggregatorMode.CBC:
                    mode_aggregator = ModeCBC(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.CFB:
                    mode_aggregator = ModeCFB(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.OFB:
                    mode_aggregator = ModeOFB(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.CTR:
                    mode_aggregator = ModeCTR(self.__block_size, self.__algorithm)
                case AggregatorMode.RD:
                    mode_aggregator = ModeRD(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.RDH:
                    mode_aggregator = ModeRDH(self.__block_size, self.__algorithm, self.__init_vector)
            while (block := f_in.read(self.__block_size * variables.BLOCK_ENCRYPT_SIZE)) and not self.__exit:
                count = self.__block_size - len(block) % self.__block_size
                f_out.write(bytes(mode_aggregator.encrypt(block + count.to_bytes(1, 'big') * count)))
                self.__progress += len(block)
                self.progress.emit(self.__progress)
        self.thread_queue.get()

    def decrypt(self, in_file: str, out_file: str):
        self.thread_queue.put(True)
        if self.__exit:
            self.thread_queue.get()
            return
        self.__progress = 0
        with (open(in_file, 'rb') as f_in,
              open(out_file, 'wb') as f_out):
            match self.__mode:
                case AggregatorMode.ECB:
                    mode_aggregator = ModeECB(self.__block_size, self.__algorithm)
                case AggregatorMode.CBC:
                    mode_aggregator = ModeCBC(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.CFB:
                    mode_aggregator = ModeCFB(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.OFB:
                    mode_aggregator = ModeOFB(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.CTR:
                    mode_aggregator = ModeCTR(self.__block_size, self.__algorithm)
                case AggregatorMode.RD:
                    mode_aggregator = ModeRD(self.__block_size, self.__algorithm, self.__init_vector)
                case AggregatorMode.RDH:
                    mode_aggregator = ModeRDH(self.__block_size, self.__algorithm, self.__init_vector)
            while (block := f_in.read(self.__block_size * (variables.BLOCK_ENCRYPT_SIZE + 3)
                                      if self.__mode == AggregatorMode.RDH else
                                      self.__block_size * (variables.BLOCK_ENCRYPT_SIZE + 1))) and not self.__exit:
                result = mode_aggregator.decrypt(block)
                del result[-result[-1]:]
                f_out.write(bytes(result))
                self.__progress += len(block)
                self.progress.emit(self.__progress)
            self.thread_queue.get()

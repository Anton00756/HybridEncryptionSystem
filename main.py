import os
from hashlib import sha256
from queue import Queue

import cryption_algorithms as alg
from simplicity_tests import TestMode


if __name__ == '__main__':
    rc = alg.RC6()
    rc.key_extension((123).to_bytes(16, 'big'))
    input_value = 12345678901234567890
    print(input_value)
    result = rc.encrypt(input_value.to_bytes(16, 'big'))
    print(int.from_bytes(rc.decrypt(result), 'big'))
    print()

    xtr = alg.XTR(TestMode.MILLER_RABIN, 0.999)
    open_keys = xtr.generate_key()

    byte_arr = bytearray([1, 2, 3])
    print(len(bytes(byte_arr).decode('utf-8')))
    print(bytes(byte_arr).decode('utf-8').encode('utf-8'))
    print(bytearray(str(byte_arr), encoding='utf-8'))

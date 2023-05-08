import algorithms


if __name__ == '__main__':
    rc = algorithms.RC6()
    rc.key_extension((123).to_bytes(16, 'big'))
    result = rc.encrypt((12345678901234567890).to_bytes(16, 'big'))
    print(result)
    print(int.from_bytes(rc.decrypt(result), 'big'))


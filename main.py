import algorithms


if __name__ == '__main__':
    rc = algorithms.RC6()
    rc.key_extension((123).to_bytes(16, 'big'))


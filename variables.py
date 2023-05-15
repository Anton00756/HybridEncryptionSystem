from typing import Final
import simplicity_tests as st

ICON_PATH: Final[str] = r'C:\Users\anton\PycharmProjects\HybridEncryptionSystem\client\images\icon.ico'
TEMP_DIR: Final[str] = r'C:\Users\anton\PycharmProjects\HybridEncryptionSystem\client\temp'
DATA_DIR: Final[str] = r'C:\Users\anton\PycharmProjects\HybridEncryptionSystem\server\data_directory'
SERVER_ADDRESS: Final[str] = 'http://127.0.0.1:5000'
BLOCK_ENCRYPT_SIZE: Final[int] = 10000
RC6_WORD_BIT_SIZE: Final[int] = 64
RC6_ROUND_COUNT: Final[int] = 20
RC6_KEY_BYTE_SIZE: Final[int] = 16
THREAD_QUEUE_SIZE: Final[int] = 3
TEST: Final[st.TestMode] = st.TestMode.MILLER_RABIN
TEST_PRECISION: Final[float] = 0.999
XTR_KEY_BIT_SIZE: Final[int] = 128
MAX_BYTE_FILE_SIZE: Final[int] = 50 * 1024 * 1024

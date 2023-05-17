import base64
import os
import time
from uuid import uuid4
from typing import Optional, Tuple
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import variables
from client.compiled_ui.file_manager import Ui_FileManager
import requests
import json
from cryption_algorithms import RC6
import file_encryption as fe
import cryption_algorithms as ca
from variables import SERVER_ADDRESS


def convert_bytes(bytes_to_convert: bytes) -> str:
    return base64.b64encode(bytes_to_convert).decode()


def convert_str(str_to_convert: str) -> bytes:
    return base64.b64decode(str_to_convert)


class Runner(QObject):
    finished = pyqtSignal()
    byte_size = pyqtSignal(int)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(str)

    def __init__(self, user_id: int, file_path: str, mode: int, new_path: str, file_id: Optional[int]) -> None:
        super(Runner, self).__init__()
        self.__user = user_id
        self.__file_path = file_path
        self.__mode = fe.AggregatorMode(mode)
        self.__new_path = new_path
        self.done = False
        self.encrypter = None
        self.__exit = False
        self.__file_id = file_id

    def close_file_worker(self):
        self.__exit = True
        if self.encrypter is not None:
            self.encrypter.shutdown()

    @staticmethod
    def get_symmetric_key() -> Tuple[int, Tuple[int, int], bytes]:
        try:
            response = requests.get(f"{SERVER_ADDRESS}/key/asymmetric/")
            if response.status_code != 200:
                raise ValueError("Не удалось получить корректный ответ от сервера!")
            result = json.loads(response.text)
            key = ca.XTR.get_symmetric_key(result['p'], result['q'], result['tr'], result['tr_k'])
            return result['key_index'], key[0], key[1]
        except requests.ConnectionError:
            raise ValueError("Не удалось подключиться к серверу!")

    def send_to_server(self, key_index: int, tr_g_b: Tuple[int, int], sym_key: bytes, old_file_name: str,
                       new_file_path: str, init_vector: Optional[bytes]) -> None:
        try:
            new_name = new_file_path[new_file_path.rfind('\\') + 1:]
            response = requests.post(f"{SERVER_ADDRESS}/file", files={'file': open(new_file_path, 'rb')},
                                     data=dict(name=new_name))
            if response.status_code != 200:
                raise ValueError("Не удалось получить корректный ответ от сервера!")
            response = requests.post(f"{SERVER_ADDRESS}/file/info", json=json.dumps(
                dict(key_index=key_index, tr_g_b=tr_g_b, sym_key=convert_bytes(bytes(sym_key)),
                     old_name=old_file_name, new_name=new_name, mode=self.__mode.value, owner=self.__user,
                     vector=None if init_vector is None else convert_bytes(bytes(init_vector)))))
            if response.status_code != 200:
                raise ValueError("Не удалось получить корректный ответ от сервера!")
        except requests.ConnectionError:
            raise ValueError("Не удалось подключиться к серверу!")

    def encrypt(self):
        algorithm = RC6(variables.RC6_WORD_BIT_SIZE, variables.RC6_ROUND_COUNT, variables.RC6_KEY_BYTE_SIZE)
        key = bytearray(os.urandom(variables.RC6_KEY_BYTE_SIZE))
        vector = None if self.__mode == fe.AggregatorMode.ECB or self.__mode == fe.AggregatorMode.CTR else \
            bytearray(os.urandom(variables.RC6_WORD_BIT_SIZE >> 1))
        self.encrypter = fe.Encrypter(algorithm, key, self.__mode, vector, block_size=variables.RC6_WORD_BIT_SIZE >> 1)
        self.encrypter.progress.connect(self.progress)
        try:
            data_for_send = self.get_symmetric_key()
            if len(key) > len(data_for_send[2]):
                raise ValueError("Выявлено несоответствие установочных данных!\n"
                                 "Ключ не должен быть больше двойной длины элемента следа!")
            self.status.emit('Шифрование:')
            self.encrypter.encrypt(self.__file_path, self.__new_path)
            if not self.__exit:
                self.status.emit('Отправка файла...')
                encrypted_key = bytes(pair[0] ^ pair[1] for pair in zip(key, data_for_send[2]))
                self.send_to_server(data_for_send[0], data_for_send[1], encrypted_key,
                                    self.__file_path[self.__file_path.rfind("/") + 1:], self.__new_path, vector)
                self.status.emit('Файл отправлен')
                os.remove(self.__new_path)
                time.sleep(0.5)
                self.result.emit('')
        except Exception as e:
            self.result.emit(e.args[0])
        self.done = True
        self.finished.emit()

    def download_from_server(self, open_key, el_gamal_key) -> Tuple[Optional[bytes], bytes, Tuple[int, int]]:
        try:
            response = requests.get(f"{SERVER_ADDRESS}/file/{self.__file_id}")
            if response.status_code != 200:
                raise ValueError("Не удалось получить корректный ответ от сервера!")
            with open(self.__new_path, 'wb') as f:
                f.write(response.content)
            response = requests.get(f"{SERVER_ADDRESS}/file/info/",
                                    json=json.dumps(dict(p=open_key[0], q=open_key[1], tr=open_key[2],
                                                         tr_k=el_gamal_key[1], file_id=self.__file_id)))
            if response.status_code != 200:
                raise ValueError("Не удалось получить корректный ответ от сервера!")
            result = json.loads(response.text)
            self.__mode = fe.AggregatorMode(result['mode'])
            return (None if result['init_vector'] == '' else convert_str(result['init_vector'])),\
                convert_str(result['key']), result['tr']
        except requests.ConnectionError:
            raise ValueError("Не удалось подключиться к серверу!")

    def decrypt(self):
        self.status.emit('Скачивание файла...')
        xtr = ca.XTR(variables.TEST, variables.TEST_PRECISION, variables.XTR_KEY_BIT_SIZE)
        try:
            open_key = xtr.generate_key()
            el_gamal_key = xtr.get_el_gamal_key()
            data_from_download = self.download_from_server(open_key, el_gamal_key)
            key = ca.XTR.get_symmetric_key_back(open_key[0], el_gamal_key[0], data_from_download[2])
            sym_key = bytes(pair[0] ^ pair[1] for pair in zip(key, data_from_download[1]))
            self.status.emit('Дешифрование:')
            self.byte_size.emit(os.stat(self.__new_path).st_size)
            algorithm = RC6(variables.RC6_WORD_BIT_SIZE, variables.RC6_ROUND_COUNT, variables.RC6_KEY_BYTE_SIZE)
            self.encrypter = fe.Encrypter(algorithm, sym_key, self.__mode, data_from_download[0],
                                          block_size=variables.RC6_WORD_BIT_SIZE >> 1)
            self.encrypter.progress.connect(self.progress)
            self.encrypter.decrypt(self.__new_path, self.__file_path)
            if not self.__exit:
                self.status.emit('Файл дешифрован')
                os.remove(self.__new_path)
                time.sleep(0.5)
                self.result.emit('')
        except Exception as e:
            self.result.emit(e.args[0])
        self.done = True
        self.finished.emit()


class FileManager(QtWidgets.QDialog):
    delete = QtCore.pyqtSignal(int)

    def __init__(self, icon: QtGui.QIcon, user_id: int, file_path: str, mode: int, index: int,
                 file_id: Optional[int] = None):
        super(FileManager, self).__init__()
        self.ui = Ui_FileManager()
        self.ui.setupUi(self)
        self.__name = file_path[file_path.rfind("/") + 1:]
        self.index = index
        self.setWindowTitle(f'[HES] {self.__name}')
        self.setLayout(self.ui.verticalLayout)
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.ui.progressBar.setMaximum(os.stat(file_path).st_size if file_id is None else 100)
        self.__new_path = os.path.join(variables.TEMP_DIR, str(uuid4()))

        self.thread = QThread()
        self.worker = Runner(user_id, file_path, mode, self.__new_path, file_id)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.encrypt if file_id is None else self.worker.decrypt)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.status.connect(lambda value: self.ui.label.setText(value))
        self.worker.progress.connect(lambda value: self.ui.progressBar.setValue(value))
        self.worker.byte_size.connect(lambda value: self.ui.progressBar.setMaximum(value))
        self.worker.result.connect(self.file_result)
        self.thread.start()

    def file_result(self, message: str):
        if message != '':
            QtWidgets.QMessageBox.critical(self, "[HES] Ошибка файла", f'\t{self.__name}:\n{message}')
        else:
            self.ui.progressBar.setValue(self.ui.progressBar.maximum())
        self.close()

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if not self.worker.done:
            self.worker.close_file_worker()
            self.worker.finished.emit()
        if self.index is not None:
            self.delete.emit(self.index)
        a0.accept()

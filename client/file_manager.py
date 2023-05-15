import os
import time
from uuid import uuid4
from time import sleep
from typing import Optional, Tuple

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import QTimer, QObject, pyqtSignal, QThread

import variables
from client.compiled_ui.file_manager import Ui_FileManager
import requests
import json

from cryption_algorithms import RC6
import file_encryption as fe
import cryption_algorithms as ca
from variables import SERVER_ADDRESS


class Runner(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(str)

    def __init__(self, user_id: int, file_path: str, mode: int, new_path: str):
        super(Runner, self).__init__()
        self.__user = user_id
        self.__file_path = file_path
        self.__mode = fe.AggregatorMode(mode)
        self.__new_path = new_path
        self.done = False
        self.encrypter = None

    def close_encrypter(self):
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
            print(sym_key, init_vector)
            response = requests.post(f"{SERVER_ADDRESS}/file/info",
                                     json=json.dumps(dict(key_index=key_index, tr_g_b=tr_g_b,
                                                          sym_key=str(bytes(sym_key)),
                                                          old_name=old_file_name, new_name=new_name,
                                                          mode=self.__mode.value, owner=self.__user,
                                                          vector=str(bytes(init_vector)))))
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
            self.status.emit('Отправка файла...')
            print('key:', key)
            encrypted_key = bytearray(pair[0] ^ pair[1] for pair in zip(key, data_for_send[2]))
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


class FileManager(QtWidgets.QDialog):
    delete = QtCore.pyqtSignal(int)

    def __init__(self, icon: QtGui.QIcon, user_id: int, file_path: str, mode: int, index: int):
        super(FileManager, self).__init__()
        self.ui = Ui_FileManager()
        self.ui.setupUi(self)
        self.__name = file_path[file_path.rfind("/") + 1:]
        self.index = index
        self.setWindowTitle(f'[HES] {self.__name}')
        self.setLayout(self.ui.verticalLayout)
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.ui.progressBar.setMaximum(os.stat(file_path).st_size)
        self.__new_path = os.path.join(variables.TEMP_DIR, str(uuid4()))

        self.thread = QThread()
        self.worker = Runner(user_id, file_path, mode, self.__new_path)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.encrypt)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.status.connect(lambda value: self.ui.label.setText(value))
        self.worker.progress.connect(lambda value: self.ui.progressBar.setValue(value))
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
            self.worker.close_encrypter()
            self.worker.finished.emit()
        if self.index is not None:
            self.delete.emit(self.index)
        a0.accept()
        # self.ui.pushButton.clicked.connect(self.login)
        # self.ui.pushButton_2.clicked.connect(self.registration_window)
        # self.__settings = QtCore.QSettings("T-Corp.", "HES")
        # if self.__settings.contains("UserLogin"):
        #     self.ui.lineEdit.setText(self.__settings.value("UserLogin"))
        #     self.ui.lineEdit_2.setFocus()
    #
    # def registration_window(self):
    #     registration = RegWindow(self.windowIcon())
    #     registration.exec()
    #
    # def login(self):
    #     if not len(user_login := self.ui.lineEdit.text().strip()) or not len(self.ui.lineEdit_2.text()):
    #         QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа", "Введите логин и пароль!")
    #         return
    #     try:
    #         response = requests.get(f"{SERVER_ADDRESS}/user/login/",
    #                                 json=json.dumps(dict(login=(user_login := user_login.lower()),
    #                                                      password=hashlib.sha256(str.encode(self.ui.lineEdit_2.text()))
    #                                                      .hexdigest())))
    #         if response.status_code != 200:
    #             QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа",
    #                                           "Не удалось получить корректный ответ от сервера!")
    #             return
    #         if (index := json.loads(response.text).get('index')) is None:
    #             QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа",
    #                                           "Некорректный логин или пароль!")
    #             return
    #         self.user_index.emit(index, user_login)
    #         self.__settings.setValue("UserLogin", user_login)
    #         self.close()
    #     except requests.ConnectionError:
    #         QtWidgets.QMessageBox.critical(self, "[HES] Ошибка входа", "Не удалось подключиться к серверу!")

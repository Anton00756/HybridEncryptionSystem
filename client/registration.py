import hashlib
import json
from PyQt6 import QtWidgets, QtCore, QtGui
from client.compiled_ui.registration import Ui_Registration
import requests
from variables import SERVER_ADDRESS


class RegWindow(QtWidgets.QDialog):
    def __init__(self, icon: QtGui.QIcon):
        super(RegWindow, self).__init__()
        self.ui = Ui_Registration()
        self.ui.setupUi(self)
        self.setLayout(self.ui.verticalLayout)
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.ui.pushButton.clicked.connect(self.registration)

    def registration(self):
        try:
            if not len(self.ui.lineEdit.text().strip()):
                raise ValueError('Введите логин!')
            if not len(self.ui.lineEdit_2.text()):
                raise ValueError('Введите пароль!')
            if self.ui.lineEdit_2.text() != self.ui.lineEdit_3.text():
                raise ValueError('Пароли не совпадают!')
            if len(self.ui.lineEdit_4.text()) != 36:
                raise ValueError('Приглашение должно содержать 36 символов!')
            response = requests.post(f"{SERVER_ADDRESS}/user/reg",
                                     json=json.dumps(dict(login=self.ui.lineEdit.text().strip().lower(),
                                                          password=hashlib.sha256(str.encode(self.ui.lineEdit_2.text()))
                                                          .hexdigest(),
                                                          invitation=self.ui.lineEdit_4.text())))
            if response.status_code == 201:
                raise ValueError('Пользователь с таким логином уже существует!')
            if response.status_code == 202:
                raise ValueError('Данного приглашения не существует!')
            self.close()
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, "[HES] Ошибка регистрации", error.args[0])
        except requests.ConnectionError:
            QtWidgets.QMessageBox.critical(self, "[HES] Ошибка регистрации", "Не удалось подключиться к серверу!")

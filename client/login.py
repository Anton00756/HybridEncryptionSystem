from PyQt6 import QtWidgets, QtCore, QtGui
from client.compiled_ui.login import Ui_Login
from registration import RegWindow
import requests
import hashlib
import json
from variables import SERVER_ADDRESS


class LogWindow(QtWidgets.QDialog):
    user_index = QtCore.pyqtSignal(int)

    def __init__(self, icon: QtGui.QIcon):
        super(LogWindow, self).__init__()
        self.ui = Ui_Login()
        self.ui.setupUi(self)
        self.setLayout(self.ui.verticalLayout)
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.ui.pushButton.clicked.connect(self.login)
        self.ui.pushButton_2.clicked.connect(self.registration_window)

    def registration_window(self):
        registration = RegWindow(self.windowIcon())
        registration.exec()

    def login(self):
        if not len(self.ui.lineEdit.text().strip()) or not len(self.ui.lineEdit_2.text()):
            QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа", "Введите логин и пароль!")
            return
        try:
            response = requests.get(f"{SERVER_ADDRESS}/user/login/",
                                    json=json.dumps(dict(login=self.ui.lineEdit.text().strip().lower(),
                                                         password=hashlib.sha256(str.encode(self.ui.lineEdit_2.text()))
                                                         .hexdigest())))
            if response.status_code != 200:
                QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа",
                                              "Не удалось получить корректный ответ от сервера!")
                return
            if (result := json.loads(response.text).get("index")) is None:
                QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа",
                                              "Некорректный логин или пароль!")
                return
            self.user_index.emit(result)
            self.close()
        except requests.ConnectionError:
            QtWidgets.QMessageBox.critical(self, "[HES] Ошибка входа", "Не удалось подключиться к серверу!")

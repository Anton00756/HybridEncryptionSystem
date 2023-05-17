from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtGui import QPixmap
from client.compiled_ui.login import Ui_Login
from registration import RegWindow
import requests
import hashlib
import json
from variables import SERVER_ADDRESS


class LogWindow(QtWidgets.QDialog):
    user_index = QtCore.pyqtSignal(int, str)

    def __init__(self, icon: QtGui.QIcon):
        super(LogWindow, self).__init__()
        self.ui = Ui_Login()
        self.ui.setupUi(self)
        self.setLayout(self.ui.verticalLayout)
        self.setWindowIcon(icon)
        self.setWindowFlags(QtCore.Qt.WindowType.WindowMinimizeButtonHint | QtCore.Qt.WindowType.WindowCloseButtonHint)
        self.ui.pushButton.clicked.connect(self.login)
        self.ui.pushButton_2.clicked.connect(self.registration_window)
        self.ui.label_3.setPixmap(QPixmap('images/login.png'))
        self.__settings = QtCore.QSettings("T-Corp.", "HES")
        if self.__settings.contains("UserLogin"):
            self.ui.lineEdit.setText(self.__settings.value("UserLogin"))
            self.ui.lineEdit_2.setFocus()

    def registration_window(self):
        registration = RegWindow(self.windowIcon())
        registration.exec()

    def login(self):
        if not len(user_login := self.ui.lineEdit.text().strip()) or not len(self.ui.lineEdit_2.text()):
            QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа", "Введите логин и пароль!")
            return
        try:
            response = requests.get(f"{SERVER_ADDRESS}/user/login/",
                                    json=json.dumps(dict(login=(user_login := user_login.lower()),
                                                         password=hashlib.sha256(str.encode(self.ui.lineEdit_2.text()))
                                                         .hexdigest())))
            if response.status_code != 200:
                QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа",
                                              "Не удалось получить корректный ответ от сервера!")
                return
            if (index := json.loads(response.text).get('index')) is None:
                QtWidgets.QMessageBox.warning(self, "[HES] Ошибка входа",
                                              "Некорректный логин или пароль!")
                return
            self.user_index.emit(index, user_login)
            self.__settings.setValue("UserLogin", user_login)
            self.close()
        except requests.ConnectionError:
            QtWidgets.QMessageBox.critical(self, "[HES] Ошибка входа", "Не удалось подключиться к серверу!")

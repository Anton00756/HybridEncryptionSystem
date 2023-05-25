import json

import requests
from PyQt6.QtCore import pyqtSignal, Qt, QObject, QTimer
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtWidgets import QLabel

from variables import SERVER_ADDRESS


class Updater(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    add_file = pyqtSignal(int, str, str, str)

    def __init__(self):
        super(Updater, self).__init__()

    def run(self):
        try:
            response = requests.get(f"{SERVER_ADDRESS}/files/")
            if response.status_code != 200:
                self.error.emit("Не удалось получить корректный ответ от сервера!")
                self.finished.emit()
                return
            for file in json.loads(response.text):
                self.add_file.emit(file['file_id'], file['file_name'], file['upload_time'], file['user'])
        except requests.ConnectionError:
            self.error.emit("Не удалось подключиться к серверу!")
        self.finished.emit()


class UpdateBtn(QLabel):
    clicked = pyqtSignal()

    def __init__(self):
        super(UpdateBtn, self).__init__()
        self.setFixedSize(32, 32)
        self.setScaledContents(True)
        self.__image = QPixmap("images/update.png")
        self.setPixmap(self.__image)
        self.__finish_image = QPixmap("images/done.png")
        self.__movie = QMovie("images/updating.gif")
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.open_to_update)
        self.__block = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.update_values()

    def update_values(self):
        if not self.__block:
            self.__block = True
            self.setMovie(self.__movie)
            self.__movie.start()
            self.clicked.emit()

    def stop_updating(self):
        self.__movie.stop()
        self.setPixmap(self.__finish_image)
        self.__timer.singleShot(1000, self.open_to_update)

    def open_to_update(self):
        self.setPixmap(self.__image)
        self.__block = False

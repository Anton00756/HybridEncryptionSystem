from PyQt6.QtCore import pyqtSignal, Qt, QObject, QTimer
from PyQt6.QtWidgets import QLabel, QMessageBox, QWidget
from PyQt6.QtGui import QMovie, QPixmap


class Updater(QObject):
    finished = pyqtSignal()

    def run(self):
        print("Updating...")  # TODO: updating files
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
        if event.button() == Qt.MouseButton.LeftButton and not self.__block:
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

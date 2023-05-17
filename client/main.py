import json
import os
import sys
from typing import Optional
import requests
from PyQt6 import QtGui, QtCore
from PyQt6.QtCore import QThread, QPoint
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import *
import re
import variables
from client.compiled_ui.main_page import Ui_MainWindow
from login import LogWindow
from file_manager import FileManager
from variables import ICON_PATH, SERVER_ADDRESS
import updater
from client.file_name_item import FileNameItem


class HESApp(QMainWindow):
    def __init__(self):
        super(HESApp, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(ICON_PATH), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)

        self.user_id: Optional[int] = None
        self.user_login: Optional[str] = None
        self.hide()
        login = LogWindow(self.windowIcon())
        login.user_index.connect(self.set_user)
        login.exec()
        if self.user_id is None:
            quit(0)
        for f in os.listdir(variables.TEMP_DIR):
            os.remove(os.path.join(variables.TEMP_DIR, f))
        self.ui.dockWidget.setFixedWidth(self.ui.label.width())
        self.ui.dockWidget.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.ui.dockWidget.setAllowedAreas(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea |
                                           QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
        self.ui.dockWidgetContents.setLayout(self.ui.verticalLayout)
        self.settings = QtCore.QSettings("T-Corp.", "HES")
        self.addDockWidget(self.settings.value("DockSide", QtCore.Qt.DockWidgetArea.RightDockWidgetArea),
                           self.ui.dockWidget)
        self.ui.dockWidget.dockLocationChanged.connect(self.changed_panel_side)
        self.ui.label.setText(f"Пользователь: {self.user_id}")
        self.ui.verticalLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ui.label.setPixmap(QtGui.QPixmap("images/person.png"))
        self.ui.pushButton.setIcon(QtGui.QIcon(QtGui.QPixmap("images/quit.png")))
        self.ui.pushButton.clicked.connect(self.logout)
        self.ui.pushButton_2.setIcon(QtGui.QIcon(QtGui.QPixmap("images/invite.png")))
        self.ui.pushButton_2.clicked.connect(self.invite)

        self.ui.centralwidget.setLayout(self.ui.verticalLayout_2)
        self.ui.label_3.setPixmap(QtGui.QPixmap("images/search.png"))
        self.update_btn = updater.UpdateBtn()
        self.update_btn.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.ui.horizontalLayout.addWidget(self.update_btn)
        self.update_btn.clicked.connect(self.update_files)
        self.ui.horizontalLayout_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.ui.comboBox.setStyleSheet(self.ui.comboBox.styleSheet() +
                                       "QComboBox::down-arrow { image: url(images/arrow.png); }"
                                       "QComboBox::down-arrow:on { image: url(images/arrow_up.png); }")
        self.ui.comboBox.setCurrentIndex(self.settings.value("CryptMode", 0))
        self.ui.comboBox.currentIndexChanged.connect(lambda: self.settings.setValue("CryptMode",
                                                                                    self.ui.comboBox.currentIndex()))
        self.ui.pushButton_3.clicked.connect(self.upload_file)

        self.thread: Optional[QThread] = None
        self.updater: Optional[updater.Updater] = None
        self.file_managers = {}
        self.file_managers_count = 0

        self.ui.lineEdit.textEdited.connect(self.search_by_name)
        self.ui.lineEdit.inputRejected.connect(self.search_by_name)
        self.ui.tableWidget.setHorizontalHeaderLabels(["Название", "Дата загрузки", "Пользователь"])
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ui.tableWidget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.table_menu_show)
        self.table_menu = QMenu(self)
        download = QAction("Скачать", self.table_menu)
        download.setIcon(QIcon(QPixmap("images/download.ico")))
        download.triggered.connect(self.download_file)
        delete = QAction("Удалить", self.table_menu)
        delete.setIcon(QIcon(QPixmap("images/delete.ico")))
        delete.triggered.connect(self.delete_file)
        self.table_menu.addAction(download)
        self.table_menu.addSeparator()
        self.table_menu.addAction(delete)
        self.aim_row: int = -1

        self.showMaximized()
        self.update_btn.clicked.emit()

    def download_file(self):
        aim_file = self.ui.tableWidget.item(self.aim_row, 0)
        aim_text = aim_file.text()
        file_type = aim_text[aim_text.rfind(".") + 1:]
        file_path = QFileDialog.getSaveFileName(self, "[HES] Загрузка файла",
                                                os.path.join(self.settings.value("DownloadFolder", ""),
                                                             aim_text), f"{file_type.upper()}-файлы (*.{file_type});;"
                                                                        f"Все файлы (*.*)",
                                                options=QFileDialog.Option.DontUseNativeDialog)[0]
        if not file_path:
            return
        if file_path.rfind(".") == -1:
            file_path += f".{file_type}"
        self.settings.setValue("DownloadFolder", file_path[:file_path.rfind("/")])
        filer = FileManager(self.windowIcon(), self.user_id, file_path, self.ui.comboBox.currentIndex(),
                            self.file_managers_count, aim_file.file_id)
        self.file_managers[self.file_managers_count] = filer
        filer.delete.connect(self.delete_filer)
        filer.show()
        self.file_managers_count += 1

    def delete_file(self):
        answer = QMessageBox.question(self, "[HES] Удаление файла", "Вы точно хотите удалить этот файл?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.No:
            return
        try:
            response = requests.delete(f"{SERVER_ADDRESS}/file/delete/"
                                       f"{self.ui.tableWidget.item(self.aim_row, 0).file_id}")
            if response.status_code != 200:
                QMessageBox.warning(self, "[HES] Удаление файла", "Не удалось получить корректный ответ от сервера!")
                return
            self.update_btn.clicked.emit()
        except requests.ConnectionError:
            QMessageBox.critical(self, "[HES] Удаление файла", "Не удалось подключиться к серверу!")

    def table_menu_show(self, point: QPoint):
        self.aim_row = self.ui.tableWidget.rowAt(point.y())
        if self.aim_row == -1:
            return
        if self.ui.tableWidget.item(self.aim_row, 2).text() != self.user_login:
            self.table_menu.actions()[2].setEnabled(False)
        else:
            self.table_menu.actions()[2].setEnabled(True)
        self.table_menu.exec(self.ui.tableWidget.mapToGlobal(point))

    def search_by_name(self, text: str):
        if text == "":
            for i in range(self.ui.tableWidget.rowCount()):
                self.ui.tableWidget.showRow(i)
            return
        text = text.lower()
        try:
            for i in range(self.ui.tableWidget.rowCount()):
                if re.search(text, self.ui.tableWidget.item(i, 0).text().lower()) is None:
                    self.ui.tableWidget.hideRow(i)
                else:
                    self.ui.tableWidget.showRow(i)
        except re.error:
            pass

    def add_file_to_table(self, file_id: int, name: str, upload_time: str, user: str):
        self.ui.tableWidget.setRowCount(self.ui.tableWidget.rowCount() + 1)
        self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount() - 1, 0, FileNameItem(name, file_id))
        self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount() - 1, 1, self.prepare_item(upload_time))
        self.ui.tableWidget.setItem(self.ui.tableWidget.rowCount() - 1, 2, self.prepare_item(user))

    @staticmethod
    def prepare_item(text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setFont(QtGui.QFont("Times New Roman", 11))
        return item

    def upload_file(self):
        folder = self.settings.value("FileFolder", "")
        if (result := QFileDialog.getOpenFileName(self, "[HES] Выберите файл", folder, "Все файлы (*.*)")[0]) == '':
            return
        self.settings.setValue("FileFolder", result[:result.rfind('')])
        if os.stat(result).st_size > variables.MAX_BYTE_FILE_SIZE:
            QMessageBox.warning(self, "[HES] Ошибка", "Файл превышает установленный максимальный размер!")
            return
        filer = FileManager(self.windowIcon(), self.user_id, result, self.ui.comboBox.currentIndex(),
                            self.file_managers_count)
        self.file_managers[self.file_managers_count] = filer
        filer.delete.connect(self.delete_filer)
        filer.show()
        self.file_managers_count += 1

    def delete_filer(self, index: int):
        del self.file_managers[index]
        self.update_btn.clicked.emit()

    def update_files(self):
        self.ui.tableWidget.setSortingEnabled(False)
        self.ui.lineEdit.setText("")
        self.ui.tableWidget.setRowCount(0)
        self.thread = QThread()
        self.updater = updater.Updater()
        self.updater.moveToThread(self.thread)
        self.updater.error.connect(lambda value: QMessageBox.critical(self, "[HES] Ошибка",
                                                                      f'\tОшибка при обновлении:\n{value}'))
        self.updater.add_file.connect(self.add_file_to_table)
        self.thread.started.connect(self.updater.run)
        self.updater.finished.connect(lambda: self.update_btn.stop_updating())
        self.updater.finished.connect(self.thread.quit)
        self.updater.finished.connect(lambda: self.ui.tableWidget.setSortingEnabled(True))
        self.updater.finished.connect(self.updater.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def set_user(self, user: int, name: str):
        self.user_id = user
        self.user_login = name
        self.ui.label_2.setText(f"Привет, {name if len(name) <= 15 else name[:15] + '...'}")

    def changed_panel_side(self):
        self.settings.setValue("DockSide", self.dockWidgetArea(self.ui.dockWidget))

    def logout(self):
        self.hide()
        self.user_id = None
        login = LogWindow(self.windowIcon())
        login.user_index.connect(self.set_user)
        login.exec()
        if self.user_id is None:
            quit(0)
        self.showMaximized()

    def invite(self):
        try:
            response = requests.get(f"{SERVER_ADDRESS}/user/invite/",
                                    json=json.dumps(dict(user_id=self.user_id)))
            if response.status_code != 200:
                QMessageBox.warning(self, "[HES] Приглашение", "Не удалось получить корректный ответ от сервера!")
                return
            result = json.loads(response.text)
            QApplication.clipboard().setText(result['invitation'])
            QMessageBox.information(self, "[HES] Приглашение",
                                    f"{'Сгенерировано новое приглашение' if result['generated'] else 'Приглашение'}:\n"
                                    f"{result['invitation']}\n\n(Помещено в буфер обмена)")
        except requests.ConnectionError:
            QMessageBox.critical(self, "[HES] Приглашение", "Не удалось подключиться к серверу!")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        for manager in self.file_managers.values():
            manager.index = None
            manager.close()
        a0.accept()


if __name__ == '__main__':
    app = QApplication([])
    application = HESApp()
    application.show()
    sys.exit(app.exec())

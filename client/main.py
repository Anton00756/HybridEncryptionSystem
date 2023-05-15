import json
import os
import sys
import time
from typing import Optional
import requests
from PyQt6 import QtGui, QtCore
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import *

import variables
from client.compiled_ui.main_page import Ui_MainWindow
from login import LogWindow
from file_manager import FileManager
from variables import ICON_PATH, SERVER_ADDRESS
import updater

"""
python -m PyQt6.uic.pyuic -x client/raw_ui/main_page.ui -o client/compiled_ui/main_page.py
python -m PyQt6.uic.pyuic -x client/raw_ui/login.ui -o client/compiled_ui/login.py
python -m PyQt6.uic.pyuic -x client/raw_ui/registration.ui -o client/compiled_ui/registration.py
python -m PyQt6.uic.pyuic -x client/raw_ui/file_manager.ui -o client/compiled_ui/file_manager.py
"""


class HESApp(QMainWindow):
    def __init__(self):
        super(HESApp, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(ICON_PATH), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)

        self.user_id: Optional[int] = None
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
        self.update_btn = elements.UpdateBtn()
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
        self.updater: Optional[elements.Updater] = None
        self.file_managers = {}
        self.file_managers_count = 0

        self.showMaximized()

    def upload_file(self):
        folder = self.settings.value("FileFolder", "")
        if (result := QFileDialog.getOpenFileName(self, "[HES] Выберите файл", folder, "Все файлы (*.*)")[0]) == '':
            return
        self.settings.setValue("FileFolder", result[:result.rfind('')])
        if os.stat(result).st_size > variables.MAX_BYTE_FILE_SIZE:
            QMessageBox.warning(self, "[HES] Ошибка", "Файл превышает установленный максимальный размер!")
            return
        filer = FileManager(self.windowIcon(), self.user_id, result, self.ui.comboBox.currentIndex(),
                            self.file_managers_count)
        self.file_managers[self.file_managers_count] = filer
        filer.delete.connect(self.delete_filer)
        filer.show()
        self.file_managers_count += 1

        # self.thread = QThread()
        # self.updater = elements.Updater(self)
        # self.updater.moveToThread(self.thread)
        # self.thread.started.connect(self.updater.run)
        # self.updater.finished.connect(self.thread.quit)
        # self.updater.finished.connect(self.updater.deleteLater)
        # self.thread.finished.connect(self.thread.deleteLater)
        # self.thread.finished.connect(lambda: print('end'))
        # self.thread.start()

    def delete_filer(self, index: int):
        del self.file_managers[index]

    def update_files(self):
        self.thread = QThread()
        self.updater = elements.Updater()
        self.updater.moveToThread(self.thread)
        self.thread.started.connect(self.updater.run)
        self.updater.finished.connect(lambda: self.update_btn.stop_updating())
        self.updater.finished.connect(self.thread.quit)
        self.updater.finished.connect(self.updater.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def set_user(self, user: int, name: str):
        self.user_id = user
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
        self.updater.finished.emit()
        for manager in self.file_managers.values():
            manager.index = None
            manager.close()
        a0.accept()


    # def reload_actions(self):
    #     self.ui.menubar.clear()
    #     if self.user_type == User.STUDENT:
    #         button_action = QtGui.QAction(QtGui.QIcon("images/crown.png"), "", self.ui.menubar)
    #         button_action.triggered.connect(self.make_admin)
    #         self.ui.menubar.addAction(button_action)
    #     if self.user_type == User.ADMIN or self.user_type == User.TEACHER:
    #         button_action = QtGui.QAction("Создать курс", self.ui.menubar)
    #         button_action.triggered.connect(self.make_course)
    #         self.ui.menubar.addAction(button_action)
    #     button_action = QtGui.QAction("Пользователи", self.ui.menubar)
    #     button_action.triggered.connect(self.all_users)
    #     self.ui.menubar.addAction(button_action)
    #     button_action = QtGui.QAction("О пользователе", self.ui.menubar)
    #     button_action.triggered.connect(self.information)
    #     self.ui.menubar.addAction(button_action)
    #
    # def all_users(self):
    #     show_data(self, self.db.get_all_users())
    #
    # def make_course(self):
    #     course = CourseCreator(self.db)
    #     course.exec_()
    #     self.update_courses(self.ui.tabWidget.currentIndex())
    #
    # def update_courses(self, page):
    #     if not page:
    #         courses = self.db.get_all_courses()
    #         table = self.ui.tableWidget
    #     else:
    #         courses = self.db.get_my_courses()
    #         table = self.ui.tableWidget_2
    #     index = 0
    #     for course in courses:
    #         course_text = course[1]
    #         if course[2] is not None:
    #             course_text += f'\n[{course[2]}' + (']' if course[3] is None else f'; {course[3]} курс]')
    #         elif course[3] is not None:
    #             course_text += f'\n[{course[3]} курс]'
    #         btn = QPushButton(course_text)
    #         btn.setStyleSheet("border: 5px solid; background-color: #E8E8E8; border-top-color: red;"
    #                           "border-left-color: blue; border-right-color: yellow; border-bottom-color: green;"
    #                           "border-width: 5px; border-radius: 30px; font: bold \"Times New Roman\"; font-size: 17px;"
    #                           "min-width: 10em; padding: 10px; margin: 3px")
    #         btn.clicked.connect(lambda state, course_page=page, course_id=course[0]: self.open_course(course_page,
    #                                                                                                   course_id))
    #         table.setCellWidget(index // 3, index % 3, btn)
    #     self.ui.statusbar.showMessage(f"Курсов найдено: {len(courses)}")
    #
    # def open_course(self, page, number):
    #     if not page and not self.db.course_is_my(number):
    #         answer = QMessageBox.question(self, '[DLS] Подключение', "Хотите присоединиться к данному курсу?",
    #                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
    #         if answer == QMessageBox.No:
    #             return
    #         self.db.connect_to_course(number)
    #     else:
    #         self.db.update_course_log(number)
    #     course_viewer = CourseViewer(self, self.db, self.user_type, number)
    #     course_viewer.showMaximized()
    #
    # def information(self):
    #     QMessageBox().about(self, "[DLS] О пользователе", self.db.get_person_info())
    #
    # def make_admin(self):
    #     text, ok = QInputDialog.getText(self, '[DLS] Получение админки', 'Введите пароль:', QLineEdit.EchoMode.Password)
    #     if ok and text == "admin":
    #         self.db.make_admin(User.ADMIN)
    #         self.user_type = User.ADMIN
    #         self.reload_actions()
    #
    # def set_user(self, user_type):
    #     self.user_type = user_type


if __name__ == '__main__':
    app = QApplication([])
    application = HESApp()
    application.show()
    sys.exit(app.exec())

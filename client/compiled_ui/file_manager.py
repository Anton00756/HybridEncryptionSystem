# Form implementation generated from reading ui file 'client/raw_ui/file_manager.ui'
#
# Created by: PyQt6 UI code generator 6.5.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_FileManager(object):
    def setupUi(self, FileManager):
        FileManager.setObjectName("FileManager")
        FileManager.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        FileManager.resize(325, 75)
        FileManager.setMinimumSize(QtCore.QSize(325, 75))
        FileManager.setMaximumSize(QtCore.QSize(325, 75))
        self.layoutWidget = QtWidgets.QWidget(parent=FileManager)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 0, 324, 77))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(5, 10, 5, 10)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(False)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.progressBar = QtWidgets.QProgressBar(parent=self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(11)
        self.progressBar.setFont(font)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(True)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout.addWidget(self.progressBar)

        self.retranslateUi(FileManager)
        QtCore.QMetaObject.connectSlotsByName(FileManager)

    def retranslateUi(self, FileManager):
        _translate = QtCore.QCoreApplication.translate
        FileManager.setWindowTitle(_translate("FileManager", "[HES] Обработка файла"))
        self.label.setText(_translate("FileManager", "Получение асимметричного ключа..."))
        self.progressBar.setFormat(_translate("FileManager", "%p %"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    FileManager = QtWidgets.QDialog()
    ui = Ui_FileManager()
    ui.setupUi(FileManager)
    FileManager.show()
    sys.exit(app.exec())
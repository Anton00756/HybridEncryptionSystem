from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QTableWidgetItem


class FileNameItem(QTableWidgetItem):
    def __init__(self, name: str, index: int):
        super(QTableWidgetItem, self).__init__(name)
        self.file_id = index
        self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Times New Roman", 11))

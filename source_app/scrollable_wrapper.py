from PyQt6.QtWidgets import QApplication, QWidget, QScrollArea, QMainWindow, QFrame
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from source_app.data import ICON, VERSION


class ScrollableMyApp(QMainWindow):
    def __init__(self, content_widget: QWidget):
        super().__init__()
        self.base_width = 700
        self.base_height = 785
        
        self.setWindowTitle(f"ChargeGrinder v{VERSION}")
        self.setWindowIcon(QIcon(ICON))
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.content_widget = content_widget
        self.content_widget.setFixedSize(self.base_width, self.base_height)
               
        self.scroll_area.setWidget(self.content_widget)
        self.setCentralWidget(self.scroll_area)
        
        self.setFixedSize(self.base_width, self.get_window_height())
        self.update_scrollbar_visibility()
    
    def update_scrollbar_visibility(self):
        current_height = self.height()
        
        if current_height >= self.base_height:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def get_display_height(self):
        screen = QApplication.screenAt(self.pos())
        if screen is None:
            screen = QApplication.primaryScreen()
        
        return screen.availableGeometry().height()

    def get_window_height(self):
        display_height = self.get_display_height() 
        if display_height < self.base_height:
            return display_height - 50
        else:
            return self.base_height
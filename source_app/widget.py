from PyQt6.QtWidgets import QWidget, QPushButton, QLineEdit, QLabel, QLayout, QHBoxLayout, QVBoxLayout, QScrollArea
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QPoint


# Custom selectize like in shiny
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins().left()
        return size + QSize(2 * margin, 2 * margin)

    def _do_layout(self, rect, move):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        
        for item in self._items:
            widget = item.widget()
            if widget.isHidden():
                continue
            space_x = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + spacing
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0
            
            if move:
                widget.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
            
        return y + line_height - rect.y()

class SelectizeItem(QWidget):
    removed = pyqtSignal(str)

    def __init__(self, text, number=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.number = number
        self.setStyleSheet('border: 1px solid #d3c19b; background: #000000; border-radius: 3px; padding: 2px 5px;')
        self.setup_ui()

    def setup_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 2, 5, 2)
        
        # Create a widget to hold number and text labels together
        text_container = QWidget()
        text_container.setStyleSheet('background: transparent;')
        text_layout = QHBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        
        if self.number is not None:
            self.number_label = QLabel(str(self.number))
            self.number_label.setStyleSheet('background: rgba(15, 100, 100, 0.7); color: #5df2ff; border: 1px solid #5df2ff; border-radius: 3px; padding: 2px 5px;')
            text_layout.addWidget(self.number_label)
        
        self.label = QLabel(self.text)
        self.label.setStyleSheet('background: transparent; border: none; color: #EDD1AC;')
        text_layout.addWidget(self.label)
        
        self.btn_remove = QPushButton("×")
        self.btn_remove.setFixedSize(20, 20)
        
        self.layout.addWidget(text_container)
        self.layout.addWidget(self.btn_remove)
        self.btn_remove.clicked.connect(self.on_remove)

    def sizeHint(self):
        return self.layout.sizeHint()
    
    def setFont(self, font):
        self.label.setFont(font)
        if hasattr(self, 'number_label'):
            self.number_label.setFont(font)

    def on_remove(self):
        self.removed.emit(self.text)

class SelectizeWidget(QWidget):
    itemsChanged = pyqtSignal(list)
    itemRemoved = pyqtSignal(str)
    itemAdded = pyqtSignal(str, int)  # Modified to include number

    def __init__(self, parent=None, font=None):
        super().__init__(parent)
        self.font = font or QFont()
        self.setStyleSheet('color: #EDD1AC; background: transparent; border: none;')
        self.items = []
        self.item_numbers = {}  # Dictionary to store item numbers
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = FlowLayout(self.scroll_content, margin=5, spacing=5)
        self.scroll.setWidget(self.scroll_content)
        
        self.layout.addWidget(self.scroll)

    def addItems(self, items, numbers=None):
        for i, item in enumerate(items):
            number = numbers.get(item) if numbers else None
            self.add_item(item, number)

    def getItems(self):
        return self.items

    def getItemNumbers(self):
        return self.item_numbers

    def add_item(self, text, number=None, refresh=True):
        if text not in self.items:
            self.items.append(text)
            if number is not None:
                self.item_numbers[text] = number
            if refresh:
                self._refresh_items()
            self.itemsChanged.emit(self.items)
            self.itemAdded.emit(text, number if number is not None else -1)

    def remove_item(self, text, refresh=True):
        if text in self.items:
            self.items.remove(text)
            if text in self.item_numbers:
                del self.item_numbers[text]
            if refresh:
                self._refresh_items()
            self.itemsChanged.emit(self.items)
            self.itemRemoved.emit(text)

    def _refresh_items(self):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        for item in self.items:
            number = self.item_numbers.get(item)
            item_widget = SelectizeItem(item, number)
            item_widget.setFont(self.font)
            item_widget.removed.connect(self.remove_item)
            self.scroll_layout.addWidget(item_widget)

    def clear(self):
        self.items = []
        self.item_numbers = {}
        self._refresh_items()



class IntField(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setValidator(QIntValidator(0, 1000))
        self.setMaxLength(4)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet('color: #EDD1AC; background: transparent; border: none;')
        self.default_value = "0"
        self.setText(self.default_value)

    def focusInEvent(self, event):
        if self.text() == self.default_value:
            self.clear()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        txt = self.text().strip()

        if txt == "" or (txt.isdigit() and int(txt) == 0):
            self.setText(self.default_value)
        super().focusOutEvent(event)

class AllIntField(IntField):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_value = "ALL"
        self.setText(self.default_value)
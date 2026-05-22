from PyQt6.QtWidgets import QPushButton, QLabel, QGraphicsOpacityEffect
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QTimer, QEvent, QPropertyAnimation


class CustomButton(QPushButton):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self._glow_cache = {}
        self.glowImage = None
        self.animation = None

        self.flickering = False
        self.flicker_paused = False
        self.event_filter = True
        self._setup_button()

    def _setup_button(self):
        if 'geometry' in self.config:
            x, y, w, h = self.config['geometry']
            self.setGeometry(x, y, w, h)

        self.setText(self.config.get('text', ''))
        self.setCheckable(self.config.get('checkable', False))
        self.setChecked(self.config.get('checked', False))

        style = self.config.get('style', '')
        self.setStyleSheet(style if style else 'background: transparent; border: none;')

        if 'click_handler' in self.config:
            self.clicked.connect(self.config['click_handler'])

        if 'icon' in self.config:
            self.setIcon(QIcon(self.config['icon']))
            self.setIconSize(self.size())
        
        if self.isCheckable() and not self.isChecked():
            self.setIcon(QIcon())

        if 'glow' in self.config:
            if 'glow_geometry' in self.config:
                self._setup_glow_effect(self.config['glow_geometry'])
            else:
                self._setup_glow_effect(self.config['geometry'])
        
        if 'filter' in self.config:
            self.event_filter = bool(self.config['filter'])

    def _setup_glow_effect(self, geometry: tuple, enable_hover=True):
        if hasattr(self, 'glowImage') and self.glowImage:
            self.glowImage.deleteLater()
        
        self.glowImage = QLabel(self.parentWidget())
        
        if self.config['glow'] not in self._glow_cache:
            self._glow_cache[self.config['glow']] = QPixmap(self.config['glow'])
        
        pixmap = self._glow_cache[self.config['glow']].scaled(
            geometry[2], geometry[3],
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.glowImage.setPixmap(pixmap)
        
        self.glowImage.setGeometry(*geometry)
        self.glowImage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.glowImage.setVisible(False)
        self.glowImage.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.glowImage.raise_()
        
        self.opacityEffect = QGraphicsOpacityEffect(self.glowImage)
        self.opacityEffect.setOpacity(0.0)
        self.glowImage.setGraphicsEffect(self.opacityEffect)

        self.animation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)

        if enable_hover:
            self.installEventFilter(self)
        elif hasattr(self, 'event_filter'):
            self.removeEventFilter(self)

    def eventFilter(self, obj, event):
        if not self.event_filter:
            return super().eventFilter(obj, event)
    
        if obj == self and self.glowImage:
            if event.type() == QEvent.Type.Enter:
                self._start_glow()
            elif event.type() == QEvent.Type.Leave:
                self._end_glow()
        
        return super().eventFilter(obj, event)

    def _start_glow(self):
        if not self.glowImage.isVisible():
            self.glowImage.setVisible(True)
        
        self.animation.stop()
        self.animation.setDirection(QPropertyAnimation.Direction.Forward)
        self.animation.start()

    def _end_glow(self):
        self.animation.stop()
        self.animation.setDirection(QPropertyAnimation.Direction.Backward)
        self.animation.start()
        
        QTimer.singleShot(self.animation.duration(), 
                         lambda: self.glowImage.setVisible(False) 
                         if self.opacityEffect.opacity() == 0.0 
                         else None)
        
    def trigger_glow_once(self):
        if self.glowImage and self.animation:
            self.glowImage.setVisible(True)
            self.animation.stop()
            self.animation.setDirection(QPropertyAnimation.Direction.Forward)
            self.animation.start()

            QTimer.singleShot(self.animation.duration(), lambda: self._end_glow())

    def start_flickering(self):
        self.animation.setDuration(1000)
        if not self.flickering:
            self.flickering = True
            self.flicker_paused = False
            self._flicker_cycle()

    def _flicker_cycle(self):
        if not self.flickering or self.flicker_paused:
            return
        
        self.trigger_glow_once()
        QTimer.singleShot(1900, self._flicker_cycle)

    def pause_flickering(self):
        if self.flickering:
            self.flicker_paused = True
            self.animation.stop()

    def resume_flickering(self):
        if self.flickering and self.flicker_paused:
            self.flicker_paused = False
            self._flicker_cycle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.glowImage and 'glow_geometry' not in self.config:
            self.glowImage.setGeometry(self.geometry())

    def set_glow_image(self, image_path, geometry=None):
        if hasattr(self, 'glowImage') and self.glowImage:
            self.glowImage.deleteLater()
        
        self.config['glow'] = image_path
        
        if geometry:
            x, y, _, _ = self.config['geometry']
            self.config['glow_geometry'] = (geometry[0] + x, geometry[1] + y, geometry[2], geometry[3])
        elif 'glow_geometry' in self.config:
            del self.config['glow_geometry']
        
        if 'glow_geometry' in self.config:
            self._setup_glow_effect(self.config['glow_geometry'], enable_hover=False)
        else:
            self._setup_glow_effect(self.config['geometry'], enable_hover=False)
    
    @staticmethod
    def glow_multiple(buttons):
        for button in buttons:
            if isinstance(button, CustomButton):
                button.trigger_glow_once()

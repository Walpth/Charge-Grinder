import json, logging, os, threading
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from source_app.utils import *
from source.utils.discord_webhook import validate_snowflake, validate_webhook_url, SSL_CONTEXT
from source_app.settings_manager import SettingsManager
from source_app.widget import SelectizeWidget, IntField, AllIntField
from source_app.button import CustomButton
from source_app.run import VersionChecker, BotWorker
from source_app.check_interception import check_windows

class MyApp(QWidget):
    webhook_test_result = pyqtSignal(bool, str)

    # TODO: I need to decompose this shitty class a bit
    def __init__(self):
        super().__init__()

        if not check_windows(app_parent=self):
            raise SystemExit(0)

        # params
        self.hard = False
        self.count = 0
        self.team = 0
        self.sinners = []

        self.is_lux = False
        self.is_proceed = False
        self.count_exp = 1
        self.count_thd = 3

        self.selected_affinity = {i: [i] for i in range(7)}
        self.team_lux = self._day()
        self.team_lux_buttons = [self.team_lux, 3 + self._day(sin=True)]
        self.keywordless = {}
        self.webhook_settings = {
            "enabled": False,
            "url": "",
            "thread_id": "",
            "compact_mode": False,
            "ping_on_finish": False,
            "ping_role_id": ""
        }
        self.webhook_env_managed = False
        self.webhook_test_running = False
        self.thread = None
        self.worker = None

        self.load_settings()
        self._init_ui()
        self._create_buttons()
        self.webhook_test_result.connect(self._handle_webhook_test_result)

        self.setFocus()

    #     self.debug_timer = QTimer()
    #     self.debug_timer.timeout.connect(self.print_state)
    #     self.debug_timer.start(2000)  # 2000 ms = 2 sec

    # def print_state(self):
    #     print(f"Current state - Affinity: {self.team}, Priority: {self.priority}")


    ### LOAD SETTINGS FROM CONFIG FILE
    def load_settings(self):
        self.sm = SettingsManager(error_handler=self.show_error, hard=lambda: self.hard)
        self.sinner_selections = {i: self.sm.get_team(i) for i in range(17)}
        self.webhook_settings = self.sm.get_webhook()

    def show_error(self, message):
        QTimer.singleShot(0, lambda: self._show_message("Bot Warning", message, QMessageBox.Icon.Critical))

    def show_info(self, message):
        QTimer.singleShot(0, lambda: self._show_message("ChargeGrinder", message, QMessageBox.Icon.Information))

    def _show_message(self, title, message, icon):
        msg = QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setInformativeText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    ### UI
    def _init_ui(self):
        """Initialize main window settings"""
        self.background = QPixmap(Bot.APP_PTH["UI"])

        font_id = QFontDatabase.addApplicationFont(Bot.APP_PTH["ExcelsiorSans"])
        if font_id != -1: self.family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.inputField = AllIntField(self)
        self.inputField.setFont(QFont(self.family, 30))
        self.inputField.setGeometry(108, 100, 90, 50)
        self.inputField.setText("3")

        self.overlay = QLabel(self)
        overlay_pixmap = QPixmap(Bot.APP_PTH['frames'])
        self.overlay.setPixmap(overlay_pixmap)
        self.overlay.setGeometry(48, 444, 601, 296)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.guide = QLabel(self)
        self.guide.setPixmap(QPixmap(Bot.APP_PTH['guide']))
        self.guide.setGeometry(0, 0, 700, 785)
        self.guide.hide()
        self.guide_close_btn = QPushButton(self.guide)
        self.guide_close_btn.setGeometry(214, 662, 241, 74)
        self.guide_close_btn.clicked.connect(self.guide.hide)
        self.guide_close_btn.setStyleSheet('background: transparent; border: none;')

        self.progress = QLabel(self)
        self.progress.setPixmap(QPixmap(Bot.APP_PTH['progress']))
        self.progress.setGeometry(0, 0, 700, 785)
        self.progress.hide()

        self.run = QLabel(self.progress)
        self.run.setPixmap(QPixmap(Bot.APP_PTH['run']))
        self.run.hide()

        self.rerun = QLabel(self.progress)
        self.rerun.setPixmap(QPixmap(Bot.APP_PTH['rerun']))
        self.rerun.hide()

        self.pause = QLabel(self.progress)
        self.pause.setPixmap(QPixmap(Bot.APP_PTH['pause']))
        self.pause.hide()
        self.stop = QPushButton(self.pause)
        self.stop.setGeometry(358, 382, 73, 69)
        self.stop.clicked.connect(self.stop_by_user)
        self.stop.setStyleSheet('background: transparent; border: none;')
        self.play = QPushButton(self.pause)
        self.play.setGeometry(268, 382, 73, 69)
        self.play.clicked.connect(self.proceed)
        self.play.setStyleSheet('background: transparent; border: none;')

        self.warn = QLabel(self.progress)
        self.warn.setPixmap(QPixmap(Bot.APP_PTH['warning']))
        self.warn.hide()

        self.warn_txt = QLabel(self.warn)
        self.warn_txt.setFont(QFont(self.family, 25))
        self.warn_txt.setGeometry(80, 630, 540, 100)
        self.warn_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warn_txt.setStyleSheet('color: #FF8080; background: transparent; border: none;')

        self.selected_button_order = []
        self.selected_card_order = []
        self.config_widgets = []

        self.config = QLabel(self)
        self.config.setPixmap(QPixmap(Bot.APP_PTH["config"]))
        self.config.setGeometry(0, 92, 700, 693)
        self.config.hide()

        self.priority_team = QLabel(self.config)
        self.priority_team.setPixmap(QPixmap(Bot.APP_PTH[f'team{self.selected_affinity[self.team][0]}']))
        self.priority_team.setGeometry(38, 121, 301, 247)
        self.priority_team.show()

        self.combo_boxes = []
        self.selectize_widgets = []
        self.line_edits = []
        self.font_large = QFont(self.family, 18)  # Cache fonts
        self.font_medium = QFont(self.family, 15)
        self.btn_font = QFont(self.family, 20)

        hard_conf_data = [
            ("OffHard",      (43, 565, 43, 31)),
            ("hard_conf2",   (87, 31, 149, 27)),
            ("infinity",     (366, 623, 128, 26)),
            ("skip_secrets", (42, 623, 128, 26)),
            ("conf_end",     (204, 568, 128, 26)),
        ]
        self.hard_confs = []
        for key, geom in hard_conf_data:
            lbl = QLabel(self.config)
            lbl.setPixmap(QPixmap(Bot.APP_PTH[key]))
            lbl.setGeometry(*geom)
            lbl.hide()
            self.hard_confs.append(lbl)

        self.ego_panel = QLabel(self.config)
        self.ego_panel.setPixmap(QPixmap(Bot.APP_PTH["config_panel"]))
        self.ego_panel.setGeometry(0, 87, 700, 605)
        self.ego_panel.hide()

        self.grace_panel = QLabel(self.config)
        self.grace_panel.setPixmap(QPixmap(Bot.APP_PTH["grace_expand"]))
        self.grace_panel.setGeometry(0, 405, 700, 123)
        self.grace_panel.hide()

        self.lux = QLabel(self)
        self.lux.setPixmap(QPixmap(Bot.APP_PTH["Lux"]))
        self.lux.setGeometry(0, 92, 700, 295)
        self.lux.hide()

        self.exp = IntField(self.lux)
        self.exp.setFont(QFont(self.family, 30))
        self.exp.setGeometry(108, 8, 90, 50)
        self.exp.setText("1")

        self.thd = IntField(self.lux)
        self.thd.setFont(QFont(self.family, 30))
        self.thd.setGeometry(108, 78, 90, 50)
        self.thd.setText("3")

        self._init_webhook_ui()

        # self.test = QPushButton(self)
        # self.test.setText("Test")
        # self.test.setGeometry(228, 514, 169, 26)
        # self.test.show()

    def _init_webhook_ui(self):
        btn_style = (
            "QPushButton {"
            "color: #EDD1AC;"
            "background-color: rgba(0, 0, 0, 205);"
            "border: 1px solid #7B6240;"
            "border-radius: 4px;"
            "padding: 2px 8px;"
            "}"
            "QPushButton:hover {"
            "color: #5df2ff;"
            "border: 1px solid #5df2ff;"
            "}"
            "QPushButton:checked {"
            "color: #5df2ff;"
            "background-color: rgba(17, 61, 70, 205);"
            "border: 1px solid #5df2ff;"
            "}"
        )
        lbl_style = "color: #EDD1AC; background: transparent; border: none;"
        field_style = (
            "QLineEdit {"
            "color: #5df2ff;"
            "background-color: rgba(0, 0, 0, 220);"
            "border: 1px solid #d3c19b;"
            "border-radius: 4px;"
            "padding: 4px 10px;"
            "selection-background-color: #1f7380;"
            "}"
            "QLineEdit:focus {"
            "border: 1px solid #5df2ff;"
            "}"
        )
        digit_validator = QRegularExpressionValidator(QRegularExpression("^\\d{0,20}$"))

        def add_button(attr, text, parent, geometry, font_size, handler=None, checkable=False):
            button = QPushButton(text, parent)
            button.setGeometry(*geometry)
            button.setFont(QFont(self.family, font_size))
            button.setStyleSheet(btn_style)
            if checkable:
                button.setCheckable(True)
            if handler:
                button.clicked.connect(handler)
            setattr(self, attr, button)
            return button

        def add_label(attr, text, geometry, font_size, *, parent=None, style=lbl_style, align=None, wrap=False):
            label = QLabel(text, parent or self.webhook_panel)
            label.setGeometry(*geometry)
            label.setFont(QFont(self.family, font_size))
            label.setStyleSheet(style)
            if align is not None:
                label.setAlignment(align)
            label.setWordWrap(wrap)
            setattr(self, attr, label)
            return label

        def add_field(attr, geometry, placeholder="", validator=None):
            field = QLineEdit(self.webhook_panel)
            field.setGeometry(*geometry)
            field.setFont(QFont(self.family, 14))
            field.setPlaceholderText(placeholder)
            if validator:
                field.setValidator(validator)
            field.setStyleSheet(field_style)
            setattr(self, attr, field)
            return field

        add_button("webhook_open", "Discord Webhook", self.config, (44, 82, 192, 28), 13, self.toggle_webhook_panel)
        add_button("hos_mode", "Arayashu", self.config, (244, 82, 192, 28), 13, self.update_button_icons, checkable=True)

        self.webhook_panel = QFrame(self.config)
        self.webhook_panel.setGeometry(24, 104, 652, 560)
        self.webhook_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.webhook_panel.setStyleSheet(
            "QFrame {"
            "background-color: rgba(9, 9, 9, 236);"
            "border: 1px solid #7B6240;"
            "border-radius: 6px;"
            "}"
        )
        self.webhook_panel.hide()

        add_label(
            "webhook_title", "Discord Webhook Settings", (28, 18, 596, 40), 24,
            align=Qt.AlignmentFlag.AlignCenter
        )

        self.webhook_enabled = add_button(
            "webhook_enabled", "", self.webhook_panel, (34, 78, 200, 42), 17, checkable=True,
            handler=lambda: self._set_webhook_toggle_text(self.webhook_enabled, "Webhook")
        )
        add_label("webhook_lbl_url", "Webhook URL", (34, 138, 300, 28), 18)
        add_field("webhook_url", (34, 168, 582, 38), "https://discord.com/api/webhooks/...")
        self.webhook_url.setEchoMode(QLineEdit.EchoMode.Password)
        self.webhook_reveal = add_button(
            "webhook_reveal", "Show URL", self.webhook_panel, (448, 136, 168, 28), 13,
            self._toggle_webhook_url_visibility, checkable=True
        )
        add_label("webhook_lbl_thread", "Thread ID (optional)", (34, 224, 300, 28), 18)
        add_field("webhook_thread", (34, 254, 582, 38), "123456789012345678", digit_validator)

        self.webhook_compact = add_button(
            "webhook_compact", "", self.webhook_panel, (34, 312, 190, 42), 16, checkable=True,
            handler=lambda: self._set_webhook_toggle_text(self.webhook_compact, "Compact")
        )
        self.webhook_ping = add_button(
            "webhook_ping", "", self.webhook_panel, (236, 312, 190, 42), 16, checkable=True,
            handler=lambda: self._set_webhook_toggle_text(self.webhook_ping, "Ping")
        )

        add_label("webhook_lbl_role", "Ping Role ID", (34, 366, 300, 28), 18)
        add_field("webhook_role", (34, 396, 582, 38), "123456789012345678", digit_validator)
        add_label(
            "webhook_hint",
            "Webhook runs asynchronously and does not block the bot.\n"
            "Compact mode shows only run start/finish updates. For Forum/Media use Thread ID.",
            (34, 444, 582, 40),
            13,
            style="color: #bfa37e; background: transparent; border: none;",
            align=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            wrap=True
        )

        add_button("webhook_test", "Test Message", self.webhook_panel, (34, 492, 185, 49), 17, self.send_webhook_test)
        add_button("webhook_save", "Save", self.webhook_panel, (247, 492, 152, 49), 17, self.save_webhook_panel)
        add_button("webhook_close", "Close", self.webhook_panel, (428, 492, 188, 49), 17, self.toggle_webhook_panel)
        self.set_webhook_ui(self.webhook_settings)

    def set_priority(self, team=None):
        if team is None:
            team = self.team
        self.priority, self.avoid, self.priority_floors, self.avoid_floors = self.get_packs(team)
        self.all = self.get_all()

    def get_packs(self, team):
        if self.sm.config_exists(team):
            priority, avoid, priority_floors, avoid_floors = self.sm.get_config(team)
        else:
            priority = self.get_priority(team)
            avoid = self.get_avoid()
            priority_floors = {}
            avoid_floors = {}
        return priority, avoid, priority_floors, avoid_floors

    def init_widgets(self):
        for i in range(2):
            combo = QComboBox()
            combo.setFont(self.font_large)
            combo.setStyle(QStyleFactory.create('Windows'))
            combo.setStyleSheet('color: #EDD1AC; selection-background-color: transparent; outline: none; border: none;')
            combo.setFixedSize(185, 32)

            selectize = SelectizeWidget(font=self.font_medium)
            selectize.itemAdded.connect(self.handle_item_added)
            selectize.itemRemoved.connect(self.handle_item_removed)

            widget = QWidget(self.config)
            widget.setStyleSheet("background: transparent;")
            widget.setGeometry(46 + i * 323, 172, 287, 187)

            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)

            top_row = QWidget()
            top_row.setFixedSize(300, 32)
            top_layout = QHBoxLayout(top_row)
            top_layout.setContentsMargins(0, 0, 0, 0)

            top_layout.addWidget(combo)

            btn_add = QPushButton("Add")
            btn_add.setFont(self.btn_font)
            btn_add.setStyle(QStyleFactory.create('Windows'))
            btn_add.setStyleSheet('color: #EDD1AC; outline: none;')
            btn_add.setFixedSize(52, 32)

            line_edit = QLineEdit()
            line_edit.setFont(self.font_large)
            if self.hard:
                validator = QRegularExpressionValidator(QRegularExpression("^(1[0-5]|[1-9])$"))
            else:
                validator = QRegularExpressionValidator(QRegularExpression("^([1-5])$"))
            line_edit.setValidator(validator)
            line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            line_edit.setFixedSize(32, 32)
            line_edit.setStyle(QStyleFactory.create('Windows'))
            line_edit.setStyleSheet('color: #5df2ff; outline: none;')

            top_layout.addWidget(line_edit)
            top_layout.addWidget(btn_add)
            top_layout.setSpacing(10)
            top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            def make_handler(selectize_widget, combo_box, index, line_edit):
                def handler():
                    text = combo_box.currentText()
                    if not text or text not in self.available_items:
                        return
                    number = None
                    if line_edit.text():
                        try:
                            num = int(line_edit.text())
                            if 1 <= num <= 5 + int(10 * self.hard) and self.check_floor(text, num):
                                number = num
                            line_edit.clear()
                        except ValueError:
                            pass
                    selectize_widget.add_item(text, number)
                    if index == 0:
                        self.priority = selectize_widget.getItems()
                        self.priority_floors = selectize_widget.getItemNumbers()
                    else:
                        self.avoid = selectize_widget.getItems()
                        self.avoid_floors = selectize_widget.getItemNumbers()
                return handler

            btn_add.clicked.connect(make_handler(selectize, combo, i, line_edit))

            layout.addWidget(top_row, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(selectize)

            widget.show()

            self.combo_boxes.append(combo)
            self.selectize_widgets.append(selectize)
            self.line_edits.append(line_edit)  # New: store for later updates
            self.config_widgets.append(widget)

    def set_widgets(self):
        for i in range(2):
            line_edit = self.line_edits[i]
            if self.hard:
                validator = QRegularExpressionValidator(QRegularExpression("^(1[0-5]|[1-9])$"))
            else:
                validator = QRegularExpressionValidator(QRegularExpression("^([1-5])$"))
            line_edit.setValidator(validator)

        items_to_remove = set(self.priority) | set(self.avoid)
        self.available_items = [item for item in self.all if item not in items_to_remove]

        for i in range(2):
            combo = self.combo_boxes[i]
            selectize = self.selectize_widgets[i]

            combo.clear()
            combo.addItems(self.available_items)

            selectize.clear()
            if i == 0:
                for item in self.priority:
                    number = self.priority_floors.get(item)
                    selectize.add_item(item, number, refresh=False)
            else:
                for item in self.avoid:
                    number = self.avoid_floors.get(item)
                    selectize.add_item(item, number, refresh=False)
            selectize._refresh_items()

    def handle_item_added(self, item):
        if item in self.available_items:
            self.available_items.remove(item)

        if item in self.priority:
            self.avoid = [i for i in self.avoid if i != item]
        if item in self.avoid:
            self.priority = [i for i in self.priority if i != item]

        for combo in self.combo_boxes:
            current_text = combo.currentText()
            combo.clear()
            combo.addItems(self.available_items)
            if current_text in self.available_items:
                combo.setCurrentText(current_text)

    def handle_item_removed(self, item):
        # Remove from both lists (if present)
        if item in self.priority:
            self.priority.remove(item)
            if hasattr(self, 'priority_floors'):
                self.priority_floors.pop(item, None)
        if item in self.avoid:
            self.avoid.remove(item)
            if hasattr(self, 'avoid_floors'):
                self.avoid_floors.pop(item, None)

        if item not in self.available_items:
            orig_index = next((i for i, x in enumerate(self.all) if x == item), -1)
            if orig_index >= 0:
                self.available_items.insert(orig_index, item)
            else:
                self.available_items.append(item)

        for combo in self.combo_boxes:
            current_text = combo.currentText()
            combo.clear()
            combo.addItems(self.available_items)
            if current_text in self.available_items:
                combo.setCurrentText(current_text)

    def reset_to_defaults(self, team, default=True):
        # Reset the data lists to defaults
        if default:
            self.priority = self.get_priority(team)
            self.avoid = self.get_avoid()
            self.priority_floors = {}
            self.avoid_floors = {}
            self.set_card_buttons([])
            self.activate_ego_gifts({})
            buff = [1]*4 + [0]*6
            if self.hard:
                on = [False, True, False, False, False, False, False, False]
                self.set_buttons_active(on + buff)
            else:
                on = [False, True, False, False, True, False, False, False]
                self.set_buttons_active(on + buff)
            self.sm.delete_config()
            self.sm.save_settings()
        else:
            self.set_priority(team)
        self.set_widgets()

    def _day(self, sin=False):
        # perfect timezone that refreshes dailies at 12 AM
        gmt_plus_3 = timezone(timedelta(hours=3))
        now_gmt3 = datetime.now(gmt_plus_3)
        day_number = now_gmt3.weekday()
        if sin:
            return (day_number + 1) % 7
        else:
            return (day_number > 1) + (day_number > 3) - (day_number == 6)

    def get_priority(self, team):
        affinity = self.selected_affinity[team][0]
        if self.hard:
            team_data = Bot.TEAMS[list(Bot.TEAMS.keys())[affinity]]
        else:
            team_data = Bot.HARD[list(Bot.HARD.keys())[affinity]]
        return team_data.get(f"floors", [])

    def get_all(self):
        if self.hard:
            return Bot.HARD_UNIQUE
        else:
            return Bot.FLOORS_UNIQUE

    def check_floor(self, name, floor):
        if 11 > floor > 5: floor = 5
        elif floor > 10:   floor = 15

        if self.hard:
            floor_dict = Bot.HARD_FLOORS
        else:
            floor_dict = Bot.FLOORS

        if name in floor_dict[floor]:
            return True
        return False

    def get_avoid(self):
        if self.hard:
            return Bot.HARD_BANNED
        else:
            return Bot.BANNED

    def _get_button_lux(self):
        return [
            (f'team_lux{i}', {
                'geometry': (30 + 63*i + i//2, 221, 64, 68),
                'checkable': True,
                'checked': i == self._day(),
                'click_handler': self.activate_lux_teams,
                'icon': Bot.APP_PTH['affinity']
            }) for i in range(3)
        ] + [
            (f'team_lux{i + 3}', {
                'geometry': (30 + 63*(i + 3) + (i + 3)//2, 221, 64, 68),
                'checkable': True,
                'checked': i == self._day(sin=True),
                'click_handler': self.activate_lux_teams,
                'icon': Bot.APP_PTH['affinity_support']
            }) for i in range(7)
        ]

    def _get_button_keyword(self):
        return [
            (f'keyword{i}', {
                'geometry': (30 + 63*i + i//2 + 191 - (i > 6)*(191 + 444), 313, 64, 68),
                'checkable': True,
                'checked': i == 0,
                'id': i,
                'click_handler': self.activate_keyword_button,
                'icon': Bot.APP_PTH['affinity'],
            }) for i in range(10)
        ]

    def _get_keyword_icon(self):
        return [
            (f'icon{i}', {
                'geometry': (221 + 63*i + (i)//2 - i//4, 242, 64, 68),
                'id': i,
                'icon': Bot.APP_PTH[f't{i}'],
            }) for i in range(7)
        ]

    def _get_button_affinity(self):
        return [
            (f'team{i}', {
                'geometry': (220 + 63*i + (i + 1)//2, 241, 64, 68),
                'checkable': True,
                'checked': i == 0,
                'click_handler': self.activate_permanent_button,
                'icon': Bot.APP_PTH['affinity'],
            }) for i in range(7)
        ]

    def _get_button_on(self):
        return [
            (f'on{i}', {
                'geometry': (30 + 162*i - (162*4 - 2)*(i > 3) - i//2, 557 + 55*(i > 3), 154, 49),
                'checkable': True,
                'checked': i == 1 or i == 4,
                'click_handler': self.update_button_icons,
                'icon': Bot.APP_PTH[f'sel{"1"*(i == 0)}_extra'],
                'glow': Bot.APP_PTH['sel_extra'],
            }) for i in range(7)
        ] + [
            (f'on{i+7}', {
                'geometry': (223 + 89*i - (i // 3) - (i == 2), 155, 85, 56),
                'checkable': True,
                'checked': i != 1,
                'click_handler': self.update_button_icons,
                'icon': Bot.APP_PTH['sel_lux']
            }) for i in range(5)
        ]

    def _get_buff(self):
        return [
            (f'buff{i}', {
                'geometry': (31 + 64*i, 416, 64, 68),
                'checkable': True,
                'checked': True,
                'id': i,
                'state': 1,
                'click_handler': self.update_buff_icons,
                'icon': Bot.APP_PTH['affinity_support']
            }) for i in range(4)
        ]

    def _get_buff_ex(self):
        return [
            (f'buff{i}', {
                'geometry': (31 + 64*i - (i//4), 11, 64, 68),
                'checkable': True,
                'checked': False,
                'id': i,
                'state': 0,
                'click_handler': self.update_buff_icons,
                'icon': Bot.APP_PTH['affinity_support']
            }) for i in range(4, 10)
        ]

    def _get_button_selected(self):
        return [
            (f'sel{i+1}', {
                'geometry': (51 + 99*(i - 6*(i > 5)), 443 + 149*(i > 5), 103, 147),
                'checkable': True,
                'checked': False,
                'id': i,
                'click_handler': self.update_selected_buttons,
            }) for i in range(12)
        ]

    def _get_card_order(self):
        return [
            (f'card{i+1}', {
                'geometry': (350 + 64*i - (i//3), 416, 64, 68),
                'checkable': True,
                'checked': False,
                'id': i,
                'click_handler': self.update_card_buttons,
            }) for i in range(5)
        ]

    def _get_ego_buttons(self):
        return [
            (f'ego{i}', {
                'geometry': (41 + 105*i - (105*6)*(i//6), 99 + 103*(i//6), 88, 87),
                'checkable': True,
                'checked': False,
                'id': i,
                'state': 0,
                'click_handler': self.update_ego_icons,
                'icon': Bot.APP_PTH['select_gift1']
            }) for i in range(24)
        ]

    def _create_buttons(self):
        """Create and configure all buttons using the CustomButton class"""
        self.buttons = {
            'update': CustomButton(self, {
                'geometry': (202, 24, 298, 53),
                'click_handler': lambda: webbrowser.open('https://github.com/Walpth/Charge-Grinder/releases/latest'),
                'checkable': True,
                'checked': True,
                'icon': Bot.APP_PTH['update'],
                'glow': Bot.APP_PTH['glow_update'],
                'filter': False
            }),

            'lux': CustomButton(self, {
                'geometry': (475, 95, 196, 57),
                'click_handler': self.set_lux,
                'glow': Bot.APP_PTH['luxbtn']
            }),

            'save': CustomButton(self, {
                'geometry': (90, 394, 125, 43),
                'click_handler': self.save,
                'glow': Bot.APP_PTH['save']
            }),

            'reset': CustomButton(self, {
                'geometry': (481, 394, 125, 43),
                'click_handler': self.reset,
                'glow': Bot.APP_PTH['clear']
            }),

            'MD': CustomButton(self.lux, {
                'geometry': (475, 3, 196, 57),
                'click_handler': self.lux_hide,
                'glow': Bot.APP_PTH['md']
            }),

            'config': CustomButton(self, {
                'geometry': (209, 164, 217, 55),
                'click_handler': lambda: (self.config.show(), self.config.raise_()),
                'glow': Bot.APP_PTH['settings']
            }),

            'save_config': CustomButton(self.config, {
                'geometry': (265, 13, 254, 63),
                'click_handler': self.save_config,
                'glow': Bot.APP_PTH['saveconf']
            }),

            'del_config': CustomButton(self.config, {
                'geometry': (530, 13, 150, 63),
                'click_handler': lambda: self.reset_to_defaults(self.team),
                'glow': Bot.APP_PTH['del']
            }),

            'ego_panel_open': CustomButton(self.config, {
                'geometry': (515, 611, 154, 49),
                'click_handler': self.toggle_ego_panel,
                'glow': Bot.APP_PTH['sel_extra']
            }),

            'ego_panel_close': CustomButton(self.ego_panel, {
                'geometry': (515, 524, 154, 49),
                'click_handler': self.toggle_ego_panel,
                'glow': Bot.APP_PTH['sel_extra']
            }),

            'grace_panel_open': CustomButton(self.config, {
                'geometry': (137, 485, 78, 31),
                'click_handler': self.toggle_grace_panel
            }),

            'grace_panel_close': CustomButton(self.grace_panel, {
                'geometry': (137, 80, 78, 31),
                'click_handler': self.toggle_grace_panel
            }),

            'hard': CustomButton(self, {
                'geometry': (24, 166, 178, 58),
                'checkable': True,
                'checked': False,
                'click_handler': self.set_hardmode,
                'icon': Bot.APP_PTH['hard']
            }),

            'log': CustomButton(self, {
                'geometry': (564, 29, 41, 40),
                'checkable': True,
                'checked': True,
                'click_handler': self.update_button_icons,
                'icon': Bot.APP_PTH['log_on']
            }),
            'csv': CustomButton(self, {
                'geometry': (523, 35, 41, 28),
                'click_handler': self.ask_csv,
                'glow': Bot.APP_PTH['csv']
            }),

            'guide_icon': CustomButton(self, {
                'geometry': (45, 25, 135, 49),
                'click_handler': self.show_guide,
                'glow': Bot.APP_PTH['guide_icon'],
            }),

            'start': CustomButton(self, {
                'geometry': (453, 165, 216, 65),
                'click_handler': self.start,
                'glow': Bot.APP_PTH['start'],
            }),

            'githubButton': CustomButton(self, {
                'geometry': (615, 33, 35, 35),
                'glow': Bot.APP_PTH['me'],
                'glow_geometry': (610, 26, 47, 47),
                'click_handler': lambda: webbrowser.open('https://github.com/Walpth/Charge-Grinder')
            })
        }
        all_buttons = self._get_keyword_icon() + self._get_button_affinity() + self._get_button_selected() + self._get_button_keyword()
        for name, settings in all_buttons:
            self.buttons[name] = CustomButton(self, settings)

        for name, settings in self._get_button_on()[:7] + self._get_card_order() + self._get_buff():
            self.buttons[name] = CustomButton(self.config, settings)

        for name, settings in self._get_button_on()[7:]:
            self.buttons[name] = CustomButton(self.lux, settings)

        for name, settings in self._get_button_lux():
            self.buttons[name] = CustomButton(self.lux, settings)

        for name, settings in self._get_ego_buttons():
            self.buttons[name] = CustomButton(self.ego_panel, settings)

        for name, settings in self._get_buff_ex():
            self.buttons[name] = CustomButton(self.grace_panel, settings)

        self.buttons['update'].hide()
        self.check_version()

        self.set_team()
        self.set_extra()
        self.priority_team.setPixmap(QPixmap(Bot.APP_PTH[f'team{self.selected_affinity[self.team][0]}']))
        self.set_priority()

        self.init_widgets()
        self.set_widgets()
        self.set_selected_buttons(self.sinner_selections[self.team])
        self.set_affinity_buttons(self.selected_affinity[self.team])
        self.activate_ego_gifts(self.sm.get_config(7))
        self.set_buttons_active(self.sm.get_config(8))
        self.set_card_buttons(self.sm.get_config(9))
        self.overlay.raise_()

    def set_team(self):
        # first 7 values - whether button is activated, last - team index
        state = self.sm.get_aff()
        if not state: return

        self.team = state["7"]
        for i in range(7):
            is_selected, self.selected_affinity[i] = state[str(i)]
            self.buttons[f"icon{i}"].setIcon(QIcon(Bot.APP_PTH[f"t{self.selected_affinity[i][0]}"]))
            if is_selected:
                self.buttons[f"team{i}"].setChecked(True)
                if i == self.team:
                    self.buttons[f"team{i}"].setIcon(QIcon(Bot.APP_PTH["affinity"]))
                else:
                    self.buttons[f"team{i}"].setIcon(QIcon(Bot.APP_PTH["affinity_support"]))
            else:
                self.buttons[f"team{i}"].setChecked(False)
                self.buttons[f"team{i}"].setIcon(QIcon())

    def set_extra(self):
        state = self.sm.get_extra()
        if not state: return

        self.inputField.setText(str(state[0]) if state[0] != -1 else "ALL")
        self.exp.setText(str(state[1]))
        self.thd.setText(str(state[2]))

        for i in range(5):
            if state[i + 3]:
                self.buttons[f"on{i + 7}"].setChecked(True)
                self.buttons[f"on{i + 7}"].setIcon(QIcon(Bot.APP_PTH["sel_lux"]))
            else:
                self.buttons[f"on{i + 7}"].setChecked(False)
                self.buttons[f"on{i + 7}"].setIcon(QIcon())

            if len(state) > 8:
                self.hos_mode.setChecked(bool(state[8]))

    def save_affinity(self):
        state = dict()
        for i in range(7):
            state[str(i)] = (self.buttons[f"team{i}"].isChecked(), self.selected_affinity[i])
        state[str(7)] = self.team
        self.sm.set_aff(state)

        extra = [self.count, self.count_exp, self.count_thd]
        for i in range(5):
            extra.append(self.buttons[f"on{i + 7}"].isChecked())
        extra.append(self.hos_mode.isChecked())
        self.sm.set_extra(extra)
        self.sync_webhook_settings(show_message=False)
        self.sm.save_settings()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.background)

    def set_hardmode(self):
        self.update_button_icons()
        self.hard = self.buttons['hard'].isChecked()
        self.set_priority()
        self.set_widgets()
        buff = [1]*4 + [0]*6
        if self.hard:
            on = [False, True, False, False, False, False, False, False]
            self.set_buttons_active(on + buff)
            self.buttons['on0'].config['icon'] = Bot.APP_PTH['sel1_hard']
            for lbl in self.hard_confs:
                lbl.show()
        else:
            on = [False, True, False, False, True, False, False, False]
            self.set_buttons_active(on + buff)
            self.buttons['on0'].config['icon'] = Bot.APP_PTH['sel1_extra']
            for lbl in self.hard_confs:
                lbl.hide()
        self.activate_ego_gifts(self.sm.get_config(7))
        self.set_buttons_active(self.sm.get_config(8))
        self.set_card_buttons(self.sm.get_config(9))

    def set_lux(self):
        self.lux.show()
        self.lux.raise_()
        self.is_lux = True
        self.buttons['start'].raise_()
        self.update_sinners()
        self.sinner_selections[self.team] = self.sinners
        self.set_selected_buttons(self.sinner_selections[self.team_lux + 7])

    @pyqtSlot()
    def lux_hide(self):
        self.is_lux = False
        self.update_sinners()
        self.sinner_selections[self.team_lux + 7] = self.sinners
        self.set_selected_buttons(self.sinner_selections[self.team])
        self.lux.hide()

    def toggle_ego_panel(self):
        if self.ego_panel.isVisible():
            self.ego_panel.hide()
        else:
            self.webhook_panel.hide()
            self.ego_panel.raise_()
            self.ego_panel.show()

    def toggle_grace_panel(self):
        if self.grace_panel.isVisible():
            self.grace_panel.hide()
        else:
            self.webhook_panel.hide()
            self.grace_panel.raise_()
            self.grace_panel.show()
            for i in range(4):
                self.buttons[f'buff{i}'].raise_()

    def toggle_webhook_panel(self):
        if self.webhook_panel.isVisible():
            self.webhook_panel.hide()
        else:
            self.ego_panel.hide()
            self.grace_panel.hide()
            self.webhook_panel.raise_()
            self.webhook_panel.show()

    def _set_webhook_toggle_text(self, button, name):
        button.setText(f"{name} {'ON' if button.isChecked() else 'OFF'}")

    def set_webhook_ui(self, data):
        bool_fields = (
            ("enabled", self.webhook_enabled),
            ("compact_mode", self.webhook_compact),
            ("ping_on_finish", self.webhook_ping)
        )
        text_fields = (
            ("url", self.webhook_url),
            ("thread_id", self.webhook_thread),
            ("ping_role_id", self.webhook_role)
        )
        for key, widget in bool_fields:
            widget.setChecked(bool(data.get(key, False)))
        for key, widget in text_fields:
            widget.setText(str(data.get(key, "")))
        for button, name in (
            (self.webhook_enabled, "Webhook"),
            (self.webhook_compact, "Compact"),
            (self.webhook_ping, "Ping")
        ):
            self._set_webhook_toggle_text(button, name)

    def _toggle_webhook_url_visibility(self):
        visible = self.webhook_reveal.isChecked()
        self.webhook_url.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        self.webhook_reveal.setText("Hide URL" if visible else "Show URL")

    def get_webhook_ui(self):
        data = {}
        for key, widget in (
            ("enabled", self.webhook_enabled),
            ("compact_mode", self.webhook_compact),
            ("ping_on_finish", self.webhook_ping)
        ):
            data[key] = widget.isChecked()
        for key, widget in (
            ("url", self.webhook_url),
            ("thread_id", self.webhook_thread),
            ("ping_role_id", self.webhook_role)
        ):
            data[key] = widget.text().strip()
        return data

    def validate_webhook(self, data, show_message=False, require_url=False):
        if not data["enabled"] and not require_url:
            return True

        if not data["url"]:
            if show_message:
                self.show_error("Discord webhook is enabled, but URL is empty." if data["enabled"] else "Webhook URL is empty.")
            return False

        checks = [
            validate_webhook_url(data["url"]),
            validate_snowflake(data["thread_id"], "Thread ID"),
            validate_snowflake(data["ping_role_id"], "Ping Role ID"),
            "Ping is enabled, but Role ID is empty." if data["ping_on_finish"] and not data["ping_role_id"] else None
        ]
        for message in checks:
            if message:
                if show_message:
                    self.show_error(message)
                return False

        return True

    def sync_webhook_settings(self, show_message=False):
        data = self.get_webhook_ui()
        if not self.validate_webhook(data, show_message=show_message):
            return False

        self.webhook_settings = data
        self.sm.set_webhook(self.webhook_settings)
        return True

    def apply_webhook_env(self):
        has_ui_url = bool(self.webhook_settings["url"])
        enabled = self.webhook_settings["enabled"]
        run_target = "ALL" if self.count == -1 else str(max(0, self.count))
        env_values = {
            "CGRINDER_DISCORD_WEBHOOK_URL": self.webhook_settings["url"],
            "CGRINDER_DISCORD_TOTAL_RUNS": run_target,
            "CGRINDER_DISCORD_EXP_TOTAL_RUNS": str(max(0, self.count_exp)),
            "CGRINDER_DISCORD_THREAD_TOTAL_RUNS": str(max(0, self.count_thd)),
            "CGRINDER_DISCORD_COMPACT_MODE": "1" if self.webhook_settings["compact_mode"] else "0",
            "CGRINDER_DISCORD_PING_ON_FINISH": "1" if self.webhook_settings["ping_on_finish"] else "0",
            "CGRINDER_DISCORD_THREAD_ID": self.webhook_settings["thread_id"],
            "CGRINDER_DISCORD_PING_ROLE_ID": self.webhook_settings["ping_role_id"]
        }
        managed_keys = tuple(env_values.keys())

        if has_ui_url:
            self.webhook_env_managed = True
            if enabled:
                for key, value in env_values.items():
                    if value:
                        os.environ[key] = value
                    else:
                        os.environ.pop(key, None)
            else:
                for key in managed_keys:
                    os.environ.pop(key, None)
            return

        if self.webhook_env_managed:
            for key in managed_keys:
                os.environ.pop(key, None)
            self.webhook_env_managed = False

    def save_webhook_panel(self):
        if not self.sync_webhook_settings(show_message=True):
            return
        self.sm.save_settings()
        self.webhook_panel.hide()

    def send_webhook_test(self):
        data = self.get_webhook_ui()
        if not self.validate_webhook(data, show_message=True, require_url=True):
            return
        if self.webhook_test_running:
            return

        self.webhook_test_running = True
        self.webhook_test.setEnabled(False)
        self.webhook_test.setText("Testing...")
        threading.Thread(target=self._send_webhook_test_request, args=(data,), daemon=True).start()

    def _build_webhook_test_request(self, data, include_thread=True):
        payload = {
            "username": "ChargeGrinder",
            "embeds": [{
                "title": "ChargeGrinder Test",
                "description": "Webhook connection from app config panel.",
                "color": 0x3498DB
            }],
            "allowed_mentions": {"parse": []}
        }

        params = {"wait": "true"}
        if include_thread and data["thread_id"]:
            params["thread_id"] = data["thread_id"]
        sep = "&" if "?" in data["url"] else "?"
        url = f"{data['url']}{sep}{urlencode(params)}"

        return Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"ChargeGrinder/{Bot.APP_VERSION} DiscordWebhook"
            },
            method="POST"
        )

    def _format_webhook_error(self, error):
        if not isinstance(error, HTTPError):
            return str(error)

        body_text = ""
        try:
            body_text = error.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            pass

        if body_text:
            try:
                data = json.loads(body_text)
                message = data.get("message")
                code = data.get("code")
                if message is not None and code is not None:
                    return f"HTTP {error.code}: {message} (code {code})"
                if message is not None:
                    return f"HTTP {error.code}: {message}"
            except Exception:
                body_text = " ".join(body_text.split())
                return f"HTTP {error.code}: {error.reason} ({body_text[:160]})"
        return f"HTTP {error.code}: {error.reason}"

    def _thread_id_test_hint(self, data, error):
        if not data.get("thread_id"):
            return ""
        if not isinstance(error, HTTPError):
            return ""
        if error.code not in (400, 403, 404):
            return ""
        return " If this webhook targets a regular channel, clear Thread ID and try again."

    def _send_webhook_test_request(self, data):
        def send_once():
            request = self._build_webhook_test_request(data, include_thread=True)
            with urlopen(request, timeout=4, context=SSL_CONTEXT):
                pass

        try:
            send_once()
            self._emit_webhook_test_result(True, "Test message sent successfully.")
            return
        except HTTPError as error:
            details = self._format_webhook_error(error)
            hint = self._thread_id_test_hint(data, error)
            self._emit_webhook_test_result(False, f"Failed to send test message: {details}{hint}")
        except Exception as error:
            details = self._format_webhook_error(error)
            self._emit_webhook_test_result(False, f"Failed to send test message: {details}")

    def _emit_webhook_test_result(self, success, message):
        try:
            self.webhook_test_result.emit(success, message)
        except RuntimeError:
            pass

    @pyqtSlot(bool, str)
    def _handle_webhook_test_result(self, success, message):
        self.webhook_test_running = False
        if not self.isVisible():
            return
        self.webhook_test.setEnabled(True)
        self.webhook_test.setText("Test Message")
        if success:
            self.show_info(message)
        else:
            self.show_error(message)

    def save(self):
        if self.is_lux:
            team = self.team_lux + 7
        else:
            team = self.team
        self.update_sinners()
        self.sm.set_team(team, self.sinners)
        self.sm.save_settings()

    def reset(self):
        self.selected_button_order.clear()
        for key, button in self.buttons.items():
            if key.startswith("sel"):
                button.setChecked(False)
                button.setIcon(QIcon())

        if self.is_lux:
            self.sinner_selections[self.team_lux + 7]
        else:
            self.sinner_selections[self.team]

    def save_config(self):
        if len(self.selected_card_order) < 5:
            frame = (10, 10, 43, 41)
            errors = list(filter(lambda i: not self.buttons[f'card{i}'].isChecked(), [i for i in range(1, 6)]))
            for i in errors:
                self.buttons[f'card{i}'].set_glow_image(Bot.APP_PTH["warn_support"], frame)
            CustomButton.glow_multiple([self.buttons[f'card{i}'] for i in errors])
            return
        if not self.sync_webhook_settings(show_message=True):
            self.webhook_panel.raise_()
            self.webhook_panel.show()
            return

        self.sm.set_config(self.team, (self.priority, self.avoid, self.priority_floors, self.avoid_floors))
        self.sm.set_config(7, {str(id): state for id, state in self.keywordless.items()})
        self.sm.set_config(8, self.get_config_buttons())
        self.sm.set_config(9, self.get_cards())
        self.sm.save_settings()
        self.ego_panel.hide()
        self.grace_panel.hide()
        self.webhook_panel.hide()
        self.config.hide()

    def update_sinners(self):
        self.sinners = [button.config.get('id') for button in self.selected_button_order]

    def get_cards(self):
        return [button.config.get('id') for button in self.selected_card_order]

    def get_config_buttons(self):
        activated = []
        for i in range(7):
            activated.append(self.buttons[f'on{i}'].isChecked())
        for i in range(10):
            activated.append(getattr(self.buttons[f'buff{i}'], 'config', {}).get('state', 0))
        activated.append(self.hos_mode.isChecked())
        return activated

    def ask_csv(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.NoIcon)
        msg.setWindowTitle("Get run stats")
        msg.setText("Do you want to export your run data from game.log to game.csv?")

        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No
        )

        response = msg.exec()

        if response == QMessageBox.StandardButton.Yes:
            self.get_csv()

    def get_csv(self):
        try:
            log_to_csv()
        except FileNotFoundError:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Error")
            msg.setText("File game.log is not found")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()


    def set_buttons_active(self, states):
        if not states: return
        if len(states) == 18 and isinstance(states[7], bool) and not isinstance(states[8], bool):
            states = states[:7] + states[8:] + [states[7]]
        on_buttons = [self.buttons[f'on{i}'] for i in range(7)]
        buff_buttons = [self.buttons[f'buff{i}'] for i in range(10)]
        buttons = on_buttons + buff_buttons
        for button, state in zip(buttons, states):
            button.setChecked(state)
            if int(state) == 1:
                icon_path = getattr(button, 'config', {}).get('icon', '')
                if icon_path:
                    button.setIcon(QIcon(icon_path))
            elif int(state) > 1:
                button.setIcon(QIcon(Bot.APP_PTH[f'grace{"+"*int(state - 1)}']))
            else:
                button.setIcon(QIcon())
            button.setIconSize(button.size())
            if 'state' in getattr(button, 'config', {}):
                button.config['state'] = int(state)
        if len(states) > 17:
            self.hos_mode.setChecked(bool(states[17]))


    def activate_ego_gifts(self, data):
        # if not sm.is_version("3.0.0"): # reset old gift selection
        #     sm.save_config(7, {}, all=True)
        #     data = {}
        #     sm.set_version(Bot.APP_VERSION)
        # if isinstance(data, list): # old format
        #     data = {}
        self.keywordless = {}
        for id in range(24):
            if str(id) in data.keys():
                state = data[str(id)]
                self.buttons[f'ego{id}'].config["state"] = state
                self.buttons[f'ego{id}'].setChecked(True)
                self.buttons[f'ego{id}'].setIcon(QIcon(Bot.APP_PTH[f'select_gift{state}']))
                self.keywordless[id] = state
            else:
                if self.buttons[f'ego{id}'].isChecked():
                    self.buttons[f'ego{id}'].config["state"] = 0
                    self.buttons[f'ego{id}'].setChecked(False)
                    self.buttons[f'ego{id}'].setIcon(QIcon())

    def activate_lux_teams(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        id = None
        for i in range(10):
            if self.buttons[f"team_lux{i}"] == sender:
                id = i
                break
        else: return
        button_group = int(id > 2) # 0 for damage, 1 for sin
        ranges = [range(3), range(3, 10)]

        # print('before')
        # print(self.team_lux)
        # print(self.team_lux_buttons)
        # print([self.buttons[f"team_lux{i}"].isChecked() for i in range(10)])
        self.update_sinners()
        self.sinner_selections[self.team_lux + 7] = self.sinners
        if id == self.team_lux: # same item is clicked
            if all(item is not None for item in self.team_lux_buttons):
                self.buttons[f"team_lux{id}"].setIcon(QIcon())
                self.team_lux_buttons[button_group] = None

                self.team_lux = self.team_lux_buttons[1 - button_group]
                self.buttons[f"team_lux{self.team_lux}"].setIcon(QIcon(Bot.APP_PTH['affinity']))
            else:
                self.buttons[f"team_lux{id}"].setChecked(True)
        elif self.team_lux not in ranges[button_group]: # different group is clicked
            self.buttons[f"team_lux{self.team_lux}"].setIcon(QIcon(Bot.APP_PTH['affinity_support']))
            self.team_lux = id
            self.buttons[f"team_lux{id}"].setIcon(QIcon(Bot.APP_PTH['affinity']))
            if self.team_lux_buttons[button_group] is not None:
                if self.team_lux_buttons[button_group] == id:
                    self.buttons[f"team_lux{id}"].setChecked(True)
                else:
                    self.buttons[f"team_lux{self.team_lux_buttons[button_group]}"].setIcon(QIcon())
                    self.buttons[f"team_lux{self.team_lux_buttons[button_group]}"].setChecked(False)
            self.team_lux_buttons[button_group] = id
        else: # same group is clicked but different item
            self.buttons[f"team_lux{self.team_lux}"].setIcon(QIcon())
            self.buttons[f"team_lux{self.team_lux}"].setChecked(False)

            self.team_lux = id
            self.team_lux_buttons[button_group] = id
            self.buttons[f"team_lux{id}"].setIcon(QIcon(Bot.APP_PTH['affinity']))
        # print("after")
        # print(self.team_lux)
        # print(self.team_lux_buttons)
        # print([self.buttons[f"team_lux{i}"].isChecked() for i in range(10)])
        self.set_selected_buttons(self.sinner_selections[self.team_lux + 7])

    def activate_permanent_button(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        self.update_sinners()
        self.sinner_selections[self.team] = self.sinners
        null_visual_state = sender.icon().isNull()

        if null_visual_state:
            sender.setIcon(QIcon(Bot.APP_PTH['affinity']))
            self.buttons[f"team{self.team}"].setIcon(QIcon(Bot.APP_PTH['affinity_support']))
            for i in range(7):
                if self.buttons[f"team{i}"] == sender:
                    self.team = i
                    break
        else:
            if sender != self.buttons[f"team{self.team}"]:
                sender.setIcon(QIcon())
            else:
                sender.setChecked(True)

        self.priority_team.setPixmap(QPixmap(Bot.APP_PTH[f'team{self.selected_affinity[self.team][0]}']))
        self.reset_to_defaults(self.team, default=False)
        self.set_selected_buttons(self.sinner_selections[self.team])
        self.set_affinity_buttons(self.selected_affinity[self.team])

    def activate_keyword_button(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        button_key = next((k for k, v in self.buttons.items() if v == sender), None)
        if not button_key:
            return

        selected_affinity_buttons = [self.buttons[f'keyword{id}'] for id in self.selected_affinity[self.team]]

        main = selected_affinity_buttons[0]
        change_icon = False

        if sender.isChecked():
            if sender not in selected_affinity_buttons:
                selected_affinity_buttons.append(sender)
        else:
            if sender in selected_affinity_buttons and len(selected_affinity_buttons) > 1:
                selected_affinity_buttons.remove(sender)
                if sender is main:
                    change_icon = True

        if change_icon:
            self.change_icon(selected_affinity_buttons[0].config.get('id'))

        for index, button in enumerate(selected_affinity_buttons):
            if index == 0:
                icon_path = Bot.APP_PTH[f'affinity']
            else:
                icon_path = Bot.APP_PTH[f'aff{index}']
            button.setIcon(QIcon(icon_path))
            button.setIconSize(button.size())

        for key, button in self.buttons.items():
            if key.startswith("keyword") and button not in selected_affinity_buttons:
                button.setIcon(QIcon())

        self.selected_affinity[self.team] = [button.config.get('id') for button in selected_affinity_buttons]

    def change_icon(self, id):
        self.buttons[f'icon{self.team}'].setIcon(QIcon(Bot.APP_PTH[f"t{id}"]))
        self.priority_team.setPixmap(QPixmap(Bot.APP_PTH[f'team{id}']))

    def update_button_icons(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        if sender.isChecked():
            icon_path = getattr(sender, 'config', {}).get('icon', '')
            if icon_path:
                sender.setIcon(QIcon(icon_path))

            names = ["on8", "on11"]
            for i in range(2):
                if sender is self.buttons[names[i]]:
                    self.buttons[names[(i + 1) % 2]].setChecked(False)
                    self.buttons[names[(i + 1) % 2]].setIcon(QIcon())
                    break
        else:
            sender.setIcon(QIcon())
        sender.setIconSize(sender.size())

    def update_ego_icons(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        id = getattr(sender, 'config', {}).get('id', None)
        state = getattr(sender, 'config', {}).get('state', None)
        if id is None or state is None:
            return

        states = [j for j in range(Bot.WORDLESS[id]['state'] + 1)]
        i = states.index(state)
        next_state = states[(i + 1) % len(states)]

        if next_state == 0:
            self.keywordless.pop(id, None)
            sender.setIcon(QIcon())
        else:
            self.keywordless[id] = next_state
            sender.setIcon(QIcon(Bot.APP_PTH[f'select_gift{next_state}']))
            if next_state != 1:
                sender.setChecked(True)
        sender.config["state"] = next_state

    def update_buff_icons(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        id = getattr(sender, 'config', {}).get('id', None)
        state = getattr(sender, 'config', {}).get('state', None)
        if id is None or state is None:
            return

        next_state = (state + 1) % 4

        if next_state == 0:
            sender.setIcon(QIcon())
        else:
            if next_state != 1:
                sender.setChecked(True)
                sender.setIcon(QIcon(Bot.APP_PTH[f'grace{"+"*(next_state - 1)}']))
            else:
                sender.setIcon(QIcon(Bot.APP_PTH['affinity_support']))
        sender.config["state"] = next_state

    def update_card_buttons(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        button_key = next((k for k, v in self.buttons.items() if v == sender), None)
        if not button_key:
            return

        if sender.isChecked():
            if sender not in self.selected_card_order:
                self.selected_card_order.append(sender)
        else:
            if sender in self.selected_card_order:
                self.selected_card_order.remove(sender)

        for index, button in enumerate(self.selected_card_order):
            icon_path = Bot.APP_PTH[f'aff{index + 1}']
            button.setIcon(QIcon(icon_path))
            button.setIconSize(button.size())

        for key, button in self.buttons.items():
            if key.startswith("card") and button not in self.selected_card_order:
                button.setIcon(QIcon())

    def update_selected_buttons(self):
        sender = self.sender()
        if not sender or not isinstance(sender, QPushButton):
            return

        button_key = next((k for k, v in self.buttons.items() if v == sender), None)
        if not button_key:
            return

        if sender.isChecked():
            if sender not in self.selected_button_order:
                self.selected_button_order.append(sender)
        else:
            if sender in self.selected_button_order:
                self.selected_button_order.remove(sender)

        for index, button in enumerate(self.selected_button_order):
            icon_path = Bot.APP_PTH[f'sel{index + 1}']
            button.setIcon(QIcon(icon_path))
            button.setIconSize(button.size())

        for key, button in self.buttons.items():
            if key.startswith("sel") and button not in self.selected_button_order:
                button.setIcon(QIcon())

    def set_selected_buttons(self, button_keys: list):
        self.selected_button_order.clear()
        self.selected_button_order = [self.buttons[f'sel{key+1}'] for key in button_keys]

        # First uncheck all selectable buttons
        for key, button in self.buttons.items():
            if key.startswith("sel"):
                button.setChecked(False)
                button.setIcon(QIcon())

        for index, button in enumerate(self.selected_button_order):
            icon_path = Bot.APP_PTH[f'sel{index + 1}']
            button.setChecked(True)
            button.setIcon(QIcon(icon_path))
            button.setIconSize(button.size())

    def set_affinity_buttons(self, button_keys: list):
        selected_affinity_buttons = [self.buttons[f'keyword{id}'] for id in button_keys]

        # First uncheck all selectable buttons
        for key, button in self.buttons.items():
            if key.startswith("keyword"):
                button.setChecked(False)
                button.setIcon(QIcon())

        for index, button in enumerate(selected_affinity_buttons):
            if index == 0:
                icon_path = Bot.APP_PTH[f'affinity']
            else:
                icon_path = Bot.APP_PTH[f'aff{index}']
            button.setChecked(True)
            button.setIcon(QIcon(icon_path))
            button.setIconSize(button.size())

    def set_card_buttons(self, button_keys: list):
        self.selected_card_order.clear()
        if not button_keys: button_keys = [1, 0, 2, 3, 4]
        self.selected_card_order = [self.buttons[f'card{key+1}'] for key in button_keys]

        # First uncheck all selectable buttons
        for key, button in self.buttons.items():
            if key.startswith("card"):
                button.setChecked(False)
                button.setIcon(QIcon())

        for index, button in enumerate(self.selected_card_order):
            icon_path = Bot.APP_PTH[f'aff{index + 1}']
            button.setChecked(True)
            button.setIcon(QIcon(icon_path))
            button.setIconSize(button.size())

    def show_guide(self):
        self.guide.raise_()
        self.guide.show()

    def check_version(self):
        self.version_thread = VersionChecker()
        self.version_thread.updateAvailable.connect(self.on_version_checked)
        self.version_thread.check()

    def on_version_checked(self, up_to_date):
        if not up_to_date:
            print("Update available!")
            self.buttons['update'].show()
            self.buttons['update'].start_flickering()

    def check_inputs(self):
        if self.is_lux and (self.count_exp + self.count_thd) < 1: return False
        return True

    def check_sinners(self):
        errors = []
        for team in self.teams.keys():
            if len(self.teams[team]["sinners"]) < 1:
                errors.append(team)

        if not errors: return True

        suffix = ''
        frame = (10, 10, 43, 41)
        if self.is_lux:
            if self.is_proceed and [i for i in errors if i < 7]:
                CustomButton.glow_multiple([self.buttons['MD']])
                return False
            errors = [i - 7 for i in errors if i >= 7]
            suffix = '_lux'

        # set up glows
        for i in errors:
            if not self.is_lux and i == self.team or self.is_lux and i == self.team_lux:
                self.buttons[f'team{suffix}{i}'].set_glow_image(Bot.APP_PTH[f"warn"], frame)
            else:
                self.buttons[f'team{suffix}{i}'].set_glow_image(Bot.APP_PTH[f"warn_support"], frame)

        # play it
        CustomButton.glow_multiple(
            [self.buttons[f'team{suffix}{i}'] for i in errors]
        )
        return False

    def get_params(self):
        # MD count
        text = self.inputField.text()
        if text != "ALL": self.count = int(text)
        else: self.count = -1

        # Lux count
        text = self.exp.text()
        if text: self.count_exp = int(text)
        else: self.count_exp = 0
        text = self.thd.text()
        if text: self.count_thd = int(text)
        else: self.count_thd = 0

        if not self.sync_webhook_settings(show_message=True):
            return False
        self.apply_webhook_env()

        # logging
        try:
            setup_logging(enable_logging=self.buttons['log'].isChecked())
        except PermissionError:
            print("No logging I guess")
            setup_logging(enable_logging=False)

        # selected teams
        self.teams = dict()
        affinity_values = [self.selected_affinity[i][0] for i in range(7)]
        counts = [affinity_values[:i].count(x) for i, x in enumerate(affinity_values)]
        duplicates = {v for v in affinity_values if affinity_values.count(v) > 1}

        self.update_sinners()
        if self.is_lux:
            self.is_proceed = self.buttons["on11"].isChecked()
            self.sinner_selections[self.team_lux + 7] = self.sinners
            for i in self.team_lux_buttons:
                if i is not None:
                    self.teams[i + 7] = {"sinners": self.sinner_selections[i + 7]}
        if not self.is_lux or self.is_proceed:
            if not self.is_lux: self.sinner_selections[self.team] = self.sinners
            for index in range(7):
                i = (self.team + index) % 7
                affinity = self.selected_affinity[i][0]
                if self.buttons[f"team{i}"].isChecked():
                    priority, avoid, priority_f, avoid_f = self.get_packs(i)
                    self.teams[i] = {
                        "duplicates": affinity in duplicates,
                        "affinity_idx": counts[i],
                        "affinity": self.selected_affinity[i],
                        "sinners": self.sinner_selections[i],
                        "priority": (priority, priority_f),
                        "avoid": (avoid, priority_f, avoid_f)
                    }


        self.settings = {
            'bonus'      : self.buttons['on0'].isChecked(),
            'collect'    : self.buttons['on10'].isChecked(),
            'restart'    : self.buttons['on1'].isChecked() if not self.is_lux else self.buttons['on7'].isChecked(),
            'altf4'      : [self.buttons['on2'].isChecked(), self.buttons['on8'].isChecked()],
            'enkephalin' : self.buttons['on3'].isChecked() if not self.is_lux else self.buttons['on9'].isChecked(),
            'skip'       : self.buttons['on4'].isChecked(),
            'wishmaking' : self.buttons['on5'].isChecked(),
            'winrate'    : self.hard or self.buttons['on6'].isChecked() if not p.HOS_MODE else self.buttons['on6'].isChecked(), # Thanks to @zombpr for finding this
            'infinity'   : self.hard and self.buttons['on6'].isChecked(),
            'hos_mode'   : self.hos_mode.isChecked(),
            'buff'       : [getattr(self.buttons[f'buff{i}'], 'config', {}).get('state', 0) for i in range(10)],
            'card'       : self.get_cards(),
            'keywordless': {Bot.WORDLESS[id]['name']: state for id, state in self.keywordless.items()}
        }
        return True

    def start(self):
        if self.thread is not None and self.thread.isRunning():
            return

        if not self.get_params():
            return
        if not self.check_inputs() or not self.check_sinners():
            self.buttons['guide_icon'].trigger_glow_once()
            return

        if self.buttons['update'].isVisible(): self.buttons['update'].pause_flickering()
        self.save_affinity()

        self.progress.raise_()
        self.progress.show()
        self.run.show()
        QApplication.processEvents()

        p.stop_event.clear()
        p.STOP_REASON = None

        self.thread = QThread()
        self.worker = BotWorker(
            self.count,
            self.count_exp,
            self.count_thd,
            self.teams,
            self.settings,
            self.hard,
            self
        )

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._on_worker_thread_finished)

        self.worker.error.connect(self.handle_bot_error)
        self.worker.warning.connect(self.handle_bot_warning)

        self.thread.start()

    @pyqtSlot()
    def _on_worker_thread_finished(self):
        self.worker = None
        self.thread = None

    @pyqtSlot()
    def to_pause(self):
        self.run.hide()
        self.rerun.hide()
        self.pause.raise_()
        self.pause.show()

    def proceed(self):
        self.pause.hide()
        self.warn.hide()
        self.rerun.raise_()
        self.rerun.show()
        p.pause_event.set()

    @pyqtSlot()
    def stop_by_user(self):
        p.STOP_REASON = "Cancelled by user"
        self.stop_execution()

    @pyqtSlot()
    def stop_execution(self):
        print("Stopping execution...")
        if p.STOP_REASON:
            logging.info(f"Execution stopped: {p.STOP_REASON}")
            p.STOP_REASON = None
        p.stop_event.set()
        p.pause_event.set()

        if self.thread is not None and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.run.hide()
        self.rerun.hide()
        self.pause.hide()
        self.progress.hide()
        self.warn.hide()

        if self.buttons['update'].isVisible(): self.buttons['update'].resume_flickering()

    def handle_bot_error(self, message):
        self.run.hide()
        self.pause.hide()
        self.rerun.hide()
        self.warn.hide()

        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Bot Error")
        msg.setText("Traceback is saved in the log file. \nError message:")
        msg.setInformativeText(message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        self.progress.hide()

    def handle_bot_warning(self, message):
        self.warn.raise_()
        self.warn_txt.setText(message)
        self.warn.show()


class ScrollableMyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_width = 700
        self.base_height = 785

        self.setWindowTitle(f"ChargeGrinder v{Bot.APP_VERSION}")
        self.setWindowIcon(QIcon(Bot.ICON))

        self.scroll_area = QScrollArea()
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = MyApp()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrollableMyApp()
    window.show()
    sys.exit(app.exec())

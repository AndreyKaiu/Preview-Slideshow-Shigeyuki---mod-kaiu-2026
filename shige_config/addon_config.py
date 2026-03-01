
import random
from os.path import join, dirname

from aqt.utils import tooltip, openLink
from aqt import (
mw, qconnect,
QCheckBox, QDialog, QDoubleSpinBox, QFrame, QHBoxLayout, QIcon, QLineEdit, QStyle, QTabWidget, QWidget, Qt,
QVBoxLayout, QLabel, QPushButton, QResizeEvent, QPixmap, QAction, gui_hooks,
)

from .shige_addons import add_shige_addons_tab
from .endroll.endroll import add_credit_tab
from .button_manager import mini_button

DEBUG_MODE = True

THE_ADDON_NAME = "🟢"
SHORT_ADDON_NAME = "🟢"
RATE_THIS = None

WIDGET_WIDTH = 500
WIDGET_HEIGHT = 500
# Width: 500, Height: 500

ADDON_PACKAGE = mw.addonManager.addonFromModule(__name__)
# ｱﾄﾞｵﾝのURLが数値であるか確認
if (isinstance(ADDON_PACKAGE, (int, float))
    or (isinstance(ADDON_PACKAGE, str)
    and ADDON_PACKAGE.isdigit())):
    RATE_THIS = True

RATE_THIS_URL = f"https://ankiweb.net/shared/review/{ADDON_PACKAGE}"
REPORT_URL = "https://github.com/AndreyKaiu/Preview-Slideshow-Shigeyuki---mod-kaiu-2026/issues"
POPUP_PNG = "popup_shige.png"

BANNAR_LABEL_WIDTH = 500
SET_LINE_EDID_WIDTH = 400
MAX_LABEL_WIDTH = 100

class MyAddonConfig(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        config = mw.addonManager.getConfig(__name__)

        self.test_func = config.get("test_func", True)

        addon_path = dirname(__file__)
        self.setWindowIcon(QIcon(join(addon_path,"icon.png")))

        # Set image on QLabel
        self.patreon_label = QLabel()
        patreon_banner_path = join(addon_path, r"banner.jpg")
        pixmap = QPixmap(patreon_banner_path)
        pixmap = pixmap.scaledToWidth(BANNAR_LABEL_WIDTH, Qt.TransformationMode.SmoothTransformation)
        self.patreon_label.setPixmap(pixmap)
        self.patreon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.patreon_label.setFixedSize(pixmap.width(), pixmap.height())
        self.patreon_label.mousePressEvent = self.open_patreon_Link
        self.patreon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.patreon_label.enterEvent = self.patreon_label_enterEvent
        self.patreon_label.leaveEvent = self.patreon_label_leaveEvent

        self.setWindowTitle(THE_ADDON_NAME)

        button = QPushButton('Save')
        button.clicked.connect(self.handle_button_clicked)
        button.clicked.connect(self.hide)
        button.setFixedWidth(100)

        button2 = QPushButton('Cancel')
        button2.clicked.connect(self.cancelSelect)
        button2.clicked.connect(self.hide)
        button2.setFixedWidth(100)

        if RATE_THIS:
            button3 = QPushButton('👍️RateThis')
            button3.clicked.connect(self.open_rate_this_Link)
            mini_button(button3)

        button4 = QPushButton("💖Patreon")
        button4.clicked.connect(self.open_patreon_Link)
        mini_button(button4)

        button5 = QPushButton("🚨Issues")
        button5.clicked.connect(lambda: openLink(REPORT_URL))
        mini_button(button5)

        layout = QVBoxLayout()


        #-----------------------------
        # self.overview_zoom_layout = self.create_spinbox(
        # "[ Home & Overview Zoom ]", 0.1, 5, self.overview_zoom, 70, 1, 0.1,"overview_zoom")

        # self.zoom_in_shortcut_layout = self.create_line_edits_and_labels(
        #     "zoom_in_shortcut", self.zoom_in_shortcut, "Zoom in Shortcut")

        # self.manually_force_zoom_checkbox = self.create_checkbox(
        #     "Do not auto save zoom values.(Ctrl + Scroll wheel)",  "manually_force_zoom")


        layout = QVBoxLayout()
        tab_widget = QTabWidget()

        # Top label (not in a tab)
        layout.addWidget(self.patreon_label)

        ### Option one tab ###
        option_one_tab = QWidget()
        option_one_layout = QVBoxLayout()
        option_one_layout.addWidget(self.create_separator())


        option_one_layout.addStretch()
        option_one_tab.setLayout(option_one_layout)

        ### Option two tab ###
        option_two_tab = QWidget()
        option_two_layout = QVBoxLayout()

        option_two_layout.addStretch()
        option_two_tab.setLayout(option_two_layout)

        ### Option three tab ###
        option_three_tab = QWidget()
        option_three_layout = QVBoxLayout()


        option_three_layout.addStretch()
        option_three_tab.setLayout(option_three_layout)

        ### Add tabs to tab widget ###
        tab_widget.addTab(option_one_tab, "option1")
        tab_widget.addTab(option_two_tab, "option2")
        tab_widget.addTab(option_three_tab, "option3")

        add_credit_tab(self, tab_widget)
        add_shige_addons_tab(self, tab_widget)

        layout.addWidget(tab_widget)

        button_layout = QHBoxLayout()
        button_layout.addWidget(button)
        button_layout.addWidget(button2)

        button_layout.addStretch()
        if RATE_THIS:
            button_layout.addWidget(button3)
        button_layout.addWidget(button4)
        button_layout.addWidget(button5)
        layout.addLayout(button_layout)

        self.setLayout(layout)


        self.adjust_self_size()


    def adjust_self_size(self):
        self.resize(WIDGET_WIDTH, WIDGET_HEIGHT)

    def resizeEvent(self, event:"QResizeEvent"):
        size = event.size()
        print(f"Width: {size.width()}, Height: {size.height()}")
        super().resizeEvent(event)




    # ﾁｪｯｸﾎﾞｯｸｽを生成する関数=======================
    def create_checkbox(self, label, attribute_name):
        checkbox = QCheckBox(label, self)
        checkbox.setChecked(getattr(self, attribute_name))

        def handler(state):
            if state == 2:
                setattr(self, attribute_name, True)
            else:
                setattr(self, attribute_name, False)

        checkbox.stateChanged.connect(handler)
        return checkbox

    # ﾁｪｯｸﾎﾞｯｸｽにﾂｰﾙﾁｯﾌﾟとﾊﾃﾅｱｲｺﾝを追加する関数=========
    def add_icon_to_checkbox(self, checkbox: QCheckBox, tooltip_text):
        qtip_style = """
            QToolTip {
                border: 1px solid black;
                padding: 5px;
                font-size: 2em;
                background-color: #303030;
                color: white;
            }
        """
        checkbox.setStyleSheet(qtip_style)
        checkbox.setToolTip(tooltip_text)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        checkbox_height = checkbox.height()
        checkbox.setIcon(QIcon(icon.pixmap(checkbox_height, checkbox_height)))
    #=================================================


    # ｾﾊﾟﾚｰﾀを作成する関数=========================
    def create_separator(self):
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("border: 1px solid gray")
        return separator
    # =================================================


    # ﾚｲｱｳﾄにｽﾍﾟｰｽを追加する関数=======================
    def add_widget_with_spacing(self, layout, widget):
        hbox = QHBoxLayout()
        hbox.addSpacing(15)  # ｽﾍﾟｰｼﾝｸﾞを追加
        hbox.addWidget(widget)
        hbox.addStretch(1)
        layout.addLayout(hbox)

    # ------------ patreon label----------------------
    def patreon_label_enterEvent(self, event):
        addon_path = dirname(__file__)
        patreon_banner_hover_path = join(addon_path, r"Patreon_banner.jpg")
        self.pixmap = QPixmap(patreon_banner_hover_path)
        self.pixmap = self.pixmap.scaledToWidth(BANNAR_LABEL_WIDTH, Qt.TransformationMode.SmoothTransformation)
        self.patreon_label.setPixmap(self.pixmap)

    def patreon_label_leaveEvent(self, event):
        addon_path = dirname(__file__)
        patreon_banner_hover_path = join(addon_path, r"banner.jpg")
        self.pixmap = QPixmap(patreon_banner_hover_path)
        self.pixmap = self.pixmap.scaledToWidth(BANNAR_LABEL_WIDTH, Qt.TransformationMode.SmoothTransformation)
        self.patreon_label.setPixmap(self.pixmap)
    # ------------ patreon label----------------------

    #-- open patreon link-----
    def open_patreon_Link(self,url):
        openLink("http://patreon.com/Shigeyuki")

    #-- open rate this link-----
    def open_rate_this_Link(self,url):
        openLink(RATE_THIS_URL)

    # --- cancel -------------
    def cancelSelect(self):

        emoticons = [":-/", ":-O", ":-|"]
        selected_emoticon = random.choice(emoticons)
        tooltip("Canceled " + selected_emoticon)

        self.close()
    #-----------------------------


    #----------------------------
    # ｽﾋﾟﾝﾎﾞｯｸｽを作成する関数=========================
    def create_spinbox(self, label_text, min_value,
                                max_value, initial_value, width,
                                decimals, step, attribute_name):
        def spinbox_handler(value):
            value = round(value, 1)
            if decimals == 0:
                setattr(self, attribute_name, int(value))
            else:
                setattr(self, attribute_name, value)

        label = QLabel(label_text, self)
        # label.setFixedWidth(200)
        spinbox = QDoubleSpinBox(self)
        spinbox.setMinimum(min_value)
        spinbox.setMaximum(max_value)
        spinbox.setValue(initial_value)
        spinbox.setFixedWidth(width)
        spinbox.setDecimals(decimals)
        spinbox.setSingleStep(step)
        spinbox.valueChanged.connect(spinbox_handler)

        layout = QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(spinbox)
        layout.addStretch()

        return layout
    #=================================================


    # # ﾃｷｽﾄﾎﾞｯｸｽを作成する関数=========================
    # def create_line_edits_and_labels(self, list_attr_name, list_items, b_name, b_index=None):
    #     main_layout = QVBoxLayout()
    #     items = list_items if isinstance(list_items, list) else [list_items]
    #     for i, item in enumerate(items):
    #         line_edit = QLineEdit(item)
    #         line_edit.textChanged.connect(lambda text,
    #                                     i=i,
    #                                     name=list_attr_name: self.update_list_item(name, i, text))
    #         line_edit.setMaximumWidth(SET_LINE_EDID_WIDTH)

    #         if i == 0:
    #             layout = QHBoxLayout()
    #             if b_index is not None:
    #                 b_name_attr = getattr(self, b_name)
    #                 label_edit = QLineEdit(b_name_attr[b_index])
    #                 label_edit.textChanged.connect(lambda text,
    #                                             i=i,
    #                                             b_name=b_name: self.update_label_item(b_name, b_index, text))
    #                 label_edit.setFixedWidth(MAX_LABEL_WIDTH)
    #                 layout.addWidget(label_edit)
    #             else:
    #                 label = QLabel(b_name)
    #                 label.setFixedWidth(MAX_LABEL_WIDTH)
    #                 layout.addWidget(label)
    #         else:
    #             label = QLabel()
    #             label.setFixedWidth(MAX_LABEL_WIDTH)
    #             layout = QHBoxLayout()
    #             layout.addWidget(label)

    #         line_edit = QLineEdit(item)
    #         line_edit.textChanged.connect(lambda text,
    #                                     i=i,
    #                                     name=list_attr_name: self.update_list_item(name, i, text))
    #         line_edit.setMaximumWidth(SET_LINE_EDID_WIDTH)
    #         layout.addWidget(line_edit)
    #         main_layout.addLayout(layout)
    #     return main_layout

    # def update_label_item(self, b_name, index, text):
    #     update_label = getattr(self,b_name)
    #     update_label[index] = text

    # def update_list_item(self, list_attr_name, index, text):
    #     list_to_update = getattr(self, list_attr_name)
    #     if isinstance(list_to_update, list):
    #         list_to_update[index] = text
    #     else:
    #         setattr(self, list_attr_name, text)
    # # ===================================================


    # ﾃｷｽﾄﾎﾞｯｸｽを作成する関数=========================
    def create_line_edits_and_labels(
            self, list_attr_name, line_edit_value, label_name, extra_func=None):
        main_layout = QVBoxLayout()
        layout = QHBoxLayout()

        label = QLabel(label_name)
        label.setFixedWidth(MAX_LABEL_WIDTH)
        layout.addWidget(label)

        line_edit = QLineEdit(line_edit_value)
        line_edit.textChanged.connect(lambda text,
            name=list_attr_name: self.update_list_item(name, 0, text, extra_func))
        line_edit.setMaximumWidth(SET_LINE_EDID_WIDTH)
        layout.addWidget(line_edit)

        main_layout.addLayout(layout)
        return main_layout

    def update_list_item(self, list_attr_name, index, text, extra_func=None):
        list_to_update = getattr(self, list_attr_name)
        if isinstance(list_to_update, list):
            list_to_update[index] = text
        else:
            setattr(self, list_attr_name, text)

        if callable(extra_func):
            extra_func()
    # ===================================================


    def handle_button_clicked(self):
        self.update_config()

        emoticons = [":-)", ":-D", ";-)"]
        selected_emoticon = random.choice(emoticons)
        tooltip("Changed setting " + selected_emoticon)
        self.close()



    def update_config(self):
        config = mw.addonManager.getConfig(__name__)

        config["test_func"] = self.test_func

        mw.addonManager.writeConfig(__name__, config)


def showMyAddonConfig():
    myAddonConfig = MyAddonConfig(mw)
    myAddonConfig.show()

def execMyAddonConfig():
    myAddonConfig = MyAddonConfig()
    myAddonConfig.exec() if hasattr(MyAddonConfig, 'exec') else myAddonConfig.exec_()

def set_config_and_menu():
    # add config
    mw.addonManager.setConfigAction(__name__, execMyAddonConfig)

    # add menu
    action = QAction(THE_ADDON_NAME, mw)
    qconnect(action.triggered, showMyAddonConfig)
    mw.form.menuTools.addAction(action)

def set_my_addon_config_startup():
    gui_hooks.main_window_did_init.append(set_config_and_menu)
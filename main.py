# Copyright: (C) tosimplicity 2019-2021 <https://github.com/tosimplicity>
# Copyright: (C) Shigeyuki 2024-2025 <http://patreon.com/Shigeyuki>
# Copyright: (C) kaiu 2025-2026 <https://github.com/AndreyKaiu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import time
import random
import logging
import anki.lang
import json
from threading import Event

from aqt.qt import QItemDelegate, QBrush, QPalette, QStyleOptionViewItem, QApplication, QColor, QPen, QWidget, QCheckBox, QCursor, QDialog, QFileDialog, QInputDialog, QMenu, QPushButton, QScrollArea, QSizePolicy, QSlider, QThreadPool, QToolTip, QVBoxLayout,QTimer, Qt

from aqt import sip
from aqt import mw, appVersion
from aqt.reviewer import replay_audio as anki_replay_audio
from aqt.browser import Browser
from aqt.browser.previewer import Previewer
from aqt.browser.previewer import MultiCardPreviewer
from aqt.utils import (showText, showInfo, tooltip, tr) 

from anki.consts import *
from . import config_addon as mcon

from aqt.browser.table.table import Table
from aqt.switch import Switch
from aqt.qt import qconnect
from anki.collection import BrowserRow
# from aqt.browser.table.table import StatusDelegate
from aqt import colors
from aqt.theme import theme_manager
# import copy
from aqt import gui_hooks


# Low-level Qt classes (layout engine) take like this
try:
    from PyQt6.QtWidgets import QAbstractItemView, QTextEdit, QFrame, QStyle, QLabel, QHBoxLayout, QVBoxLayout, QLayout, QWidgetItem, QSpacerItem, QSizePolicy, QDialogButtonBox
    from PyQt6.QtCore import QRect, QPoint, QSize, QCoreApplication
    from PyQt6.QtGui import QShortcut, QKeySequence
    pyqt_version = "PyQt6"
except ImportError:
    from PyQt5.QtWidgets import QAbstractItemView, QTextEdit, QFrame, QStyle, QLabel, QHBoxLayout, QVBoxLayout, QLayout, QWidgetItem, QSpacerItem, QSizePolicy, QDialogButtonBox
    from PyQt5.QtCore import QRect, QPoint, QSize, QCoreApplication
    from PyQ5.QtGui import QShortcut, QKeySequence
    pyqt_version = "PyQt5"

from .utils import show_text, app_version_micro
from anki.utils import pointVersion as app_version_micro
from .slideshow_media_window import SlideshowMediaWindow
from .slideshow_thread import SlideshowPreviewThread
from . import mplayer_extended

from .shige_config.shige_buttons import add_shige_buttons

logger = logging.getLogger(__name__)

MEDIAS = (".mp4", ".mkv", ".avi", ".flv", ".m4v", ".f4v", ".rmvb",
          ".mpg", ".mpeg", ".mov", ".mp3", ".flac", ".m4a")
AUDIOS = (".mp3", ".flac", ".m4a")
PICTURES = (".jpg", ".png", ".gif", ".jpeg")
INSTRUCTIONS = """1. Check/Uncheck "Slideshow On/Off" to start/stop slideshow
2. Check/Uncheck "Random Seq" to activate/disable random sequence
3. Click "||" button to pause slideshow
4. Click "|>" button to continue slideshow or go to next slide
5. Use tag like "slideshow_Xs" to indicate showing answer for X seconds
   (no time tag for question)
   for example, "slideshow_17s" for 17 seconds
6. Use tag like "slideshow_audio_replays_X" to indicate replay audio X times before going to next slide
   (no audio replay tag for question)
   for example, "slideshow_audio_replays_17" for replay 17 times
7. Use tag "slideshow_aisq" to indicate question slide is same with answer slide and answer slide should be skipped.
8. To show external media like mp4, jpg, gif.
   a. Create a field in exact name "Slideshow_External_Media"
   b. Put the file path for the external media file there like "D:/somefolder/myvideo.mp4"
   c. Root forder can also be set in settings. Like setting it to "D:/somefolder"
      then "Slideshow_External_Media" field can work in relative path like "myvideo.mp4", "sometype/blabla.png"
   d. With root folder set, if you want to use absolute path accassion occasionally,
      put "$$" before the path, like "$$D:/somefolder/myvideo.mp4"
9. Hover over buttons to see tooltips
10. Right click on the toolbox in preview window, or the external media window, to access functions.
"""

# global variable to get ref to browser window and preview window and ui elements
config = mcon.get_config()
set_slideshow_q_time_button = None
set_slideshow_a_time_button = None
change_slideshow_setting_dialog = None
external_media_show_mode_button = None
slideshow_media_window_area = [0, 0, 0, 0]
# is_timeout_special: if certain card has its own timeout setting
slideshow_profile = {"q_time": 3,
                     "a_time": 5,
                     "is_on": False,
                     "timeout": 0,
                     "is_timeout_special": False,
                     "special_timeout": 0,
                     "random_sequence": False,
                     "is_showing_question": False,
                     "showed_cards": [],
                     "should_pause": False,
                     "should_play_next": False,
                     "show_external_media_event": Event(),
                     "external_media_show_mode": "on"}


def show_simple_instruction(parent=None, txt: str=""):
    """A simple window with instructions"""
    
    dialog = QDialog(parent)
    loc = mcon.get_loc("Show_Instruction","Show Instruction") 
    dialog.setWindowTitle(loc)
    dialog.setModal(True)
    dialog.setWindowFlags(
        Qt.WindowType.Window |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.WindowCloseButtonHint
    )
    dialog.resize(600, 500)
    
    layout = QVBoxLayout()
    
    text = QTextEdit()
    text.setReadOnly(True)
    text.setText(txt)
    
    close_btn = QPushButton("OK")
    close_btn.clicked.connect(dialog.accept)
    
    layout.addWidget(text)
    layout.addWidget(close_btn)
    
    dialog.setLayout(layout)
    dialog.exec()



class Browserhistory:
    def __init__(self):
        self.history = []  # List of indexes
        self.current_position = -1  # Current position in history
        self.max_history = 3000  # Maximum history size
        self.ignore_1_add = False # Ignore one addition
    
    def add(self, index):
        """
        Adds a new index to history
        """

        #Ignore one addition
        if self.ignore_1_add:
            self.ignore_1_add = False
            return 

        # Checking if this is the same index as the last one
        if self.history and self.history[-1] == index:
            return  # Ignore the duplicate       
        
        # If we are not at the end of the story, we cut off everything that came after
        # if self.current_position < len(self.history) - 1:
        #     self.history = self.history[:self.current_position + 1]
        
        
        # Adding a new index
        self.history.append(index)

        
        
        # Limiting the history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.current_position = len(self.history) - 1

        # We don’t cut the story, we’ll save everything to the end
        self.current_position = len(self.history) - 1
        
    
    def back(self):
        """
        Returns the previous index or None if there is none
        """
        if self.current_position > 0:
            self.current_position -= 1
            return self.history[self.current_position]
        return None
    
    def forward(self):
        """
        Returns the next index or None if there is none
        """
        if self.current_position < len(self.history) - 1:
            self.current_position += 1
            return self.history[self.current_position]
        return None
    
    def can_go_back(self):
        """Is it possible to go back"""
        return self.current_position > 0
    
    def can_go_forward(self):
        """Is it possible to go back forward"""
        return self.current_position < len(self.history) - 1



class MyPrev():    
    def __init__(self, pr: Previewer):
        pr._myprev = self
        self.browser = pr._parent # type: Browser
        self.preview_window = pr # type: Previewer
        self.btn_prev = None
        self.btn_next = None
        self.btn_back = None
        self.btn_forward = None
        self.btn_back_side = None
        self.btn_play_pause = None
        self.btn_random = None
        self.btn_repeat = None
        self.btn_play_pause = None
        self.btn_step = None
        self.label_timer = None 
        self.viewed = -1
        self.idx_row_last_current = -1        
        self.icon_play = None
        self.icon_pause = None
        self.icon_step = None
        self.history = Browserhistory()




# set up slideshow_profile default value
if mcon.key_in_gs("preview_slideshow_show_question_time"):
    q_time = mcon.get_gs("preview_slideshow_show_question_time")
    try:
        q_time = int(q_time)
    except Exception:
        q_time = 3
    if q_time < 1:
        q_time = 3
    if q_time != mcon.get_gs("preview_slideshow_show_question_time"):
        mcon.set_gs("preview_slideshow_show_question_time", q_time)        
    slideshow_profile["q_time"] == q_time
if mcon.key_in_gs("preview_slideshow_show_answer_time"):
    a_time = mcon.get_gs("preview_slideshow_show_answer_time")
    try:
        a_time = int(a_time)
    except Exception:
        a_time = 5
    if a_time < 1:
        a_time = 5
    if a_time != mcon.get_gs("preview_slideshow_show_answer_time"):
        mcon.set_gs("preview_slideshow_show_answer_time", a_time)       
    slideshow_profile["a_time"] = a_time
if mcon.key_in_gs("external_media_show_mode"):
    if mcon.get_gs("external_media_show_mode") not in ["off",
                                                  "on",
                                                  "on_and_backoff_if_empty"]:
        mcon.set_gs("external_media_show_mode","on")        
    else:
        slideshow_profile["external_media_show_mode"] = mcon.get_gs("external_media_show_mode")

if mcon.key_in_gs("external_media_folder_path") and mcon.get_gs("external_media_folder_path"):
    EXTERNAL_MEDIA_ROOT = mcon.get_gs("external_media_folder_path")
else:
    EXTERNAL_MEDIA_ROOT = ""




_orig_open = Previewer.open
def new_previewer_open(self) -> None:    
    self._parent.form.tableView.setFocus()   

    self._myprev = MyPrev(self)

    preview = self
    if hasattr(preview, "_myprev"):
        gl = preview._myprev         
        gl.viewed = -1
        gl.idx_row_last_current = -1
        gl.history.history = []  # List of indexes
    
    _orig_open(self)        
Previewer.open = new_previewer_open


def setup_preview_slideshow(browser:Browser):
    # "prepare when browser window shows up."    
    logger.debug("setup_preview_slideshow(target_browser)")
    if browser:        
        logger.debug("setup_preview_slideshow browser existing")
    else:
        return

    if app_version_micro() <= 40:
        # editor is static
        form = browser.form
        form.previewButton.clicked.connect(lambda: add_slideshow_ui_to_preview_window(browser))
        return None

    # from version "2.1.41" preview button is added to editor
    original_preview_f = browser.onTogglePreview
    def onTogglePreview():
        original_preview_f()        
        add_slideshow_ui_to_preview_window(browser)
    browser.onTogglePreview = onTogglePreview

        

    # 2025-12-30    

    def update_preview_title(browserPT: Browser):        
        preview = browserPT._previewer
        if not preview:
            return
        
        if hasattr(preview, "_myprev"):
            gl = preview._myprev             
        else:
            return
        
        

        # save original title once
        if not hasattr(preview, "_orig_title"):
            preview._orig_title = preview.windowTitle()

        preview.setWindowTitle(
                f"{preview._orig_title} (Warning! No card selected.)"
            )
  
        table = browserPT.table
        total = table.len()

        if total <= 0 or not table.has_current():            
            return

        idx = table._selection_model().currentIndex()
        if not idx.isValid():            
            return
                
        current = idx.row() + 1
        if current != gl.idx_row_last_current:
            gl.viewed += 1           
            gl.history.add(current-1) 

        gl.history.ignore_1_add = False
        

        if gl.btn_back is not None and not sip.isdeleted(gl.btn_back):
            gl.btn_back.setEnabled(gl.history.can_go_back())            
        if gl.btn_forward is not None and not sip.isdeleted(gl.btn_forward):
            gl.btn_forward.setEnabled(gl.history.can_go_forward())             

        
        totasubv = total-gl.viewed-1
        if totasubv < 0:
            totasubv = 0 
        preview.setWindowTitle(
            f"{preview._orig_title}  {current} .. {total} (+{total-current});  👁: {gl.viewed+1} (+{totasubv})"
        )

        gl.idx_row_last_current = current



    _orig_render = Previewer.render_card
    def render_card_with_title(self):
        _orig_render(self)
        update_preview_title(self._parent)         

    Previewer.render_card = render_card_with_title


    

    _orig_updateButtons = MultiCardPreviewer._updateButtons 
    def _new_updateButtons(self) -> None:         
        if not self._open:
            return
        
        preview = self
        if hasattr(preview, "_myprev"):
            gl = preview._myprev             
        else:
            return

        assert self._prev is not None
        assert self._next is not None

        self._prev.setEnabled(self._should_enable_prev())
        self._next.setEnabled(self._should_enable_next()) 
        

        if gl.btn_prev is not None and not sip.isdeleted(gl.btn_prev):
            gl.btn_prev.setEnabled(self._should_enable_prev())
        if gl.btn_next is not None and not sip.isdeleted(gl.btn_next):     
            gl.btn_next.setEnabled(self._should_enable_next())     
        if gl.btn_back_side is not None and not sip.isdeleted(gl.btn_back_side):
            gl.btn_back_side.setChecked(self._show_both_sides)
        
        if gl.btn_back is not None and not sip.isdeleted(gl.btn_back):
            gl.btn_back.setEnabled(gl.history.can_go_back())
        if gl.btn_forward is not None and not sip.isdeleted(gl.btn_forward):
            gl.btn_forward.setEnabled(gl.history.can_go_forward())           
        

    MultiCardPreviewer._updateButtons = _new_updateButtons

   


def add_slideshow_ui_to_preview_window(browser: Browser):
    """ Add custom slideshow UI elements below standard preview buttons """
    logger.debug("setup_preview_slideshow(target_browser)")    

    global slideshow_profile

    preview = browser._previewer
    if hasattr(preview, "_myprev"):
        gl = preview._myprev                                                                                                                                   
    else:
        return


    

    # We get gl.preview_window
    i = 0
    # while True:
    #     try:
    #         if app_version_micro() >= 24:
    #             gl.preview_window = browser._previewer
    #         else:
    #             gl.preview_window = browser._previewWindow

    #         if gl.preview_window.isVisible():
    #             break
    #     except Exception:
    #         pass

    #     if i >= 10:
    #         gl.preview_window = None
    #         return
    #     i += 1
    #     time.sleep(0.2)

    slideshow_profile["is_on"] = False
   

    # add space and a standard panel to center it
    standard_bbox = getattr(gl.preview_window, "bbox", None)
    # if standard_bbox:
    #     layout = standard_bbox.layout()
    #     if layout is not None:
    #         layout.addSpacerItem(
    #             QSpacerItem(8, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
    #         )

    # no longer necessary, hide it       
    if standard_bbox is not None:
        standard_bbox.hide()        
    

    def show_context_menu_of_preview_window(pos):
        nonlocal gl 
        m = QMenu(gl.preview_window)
        # if not preview_slideshow_switch.isChecked():
        if not gl.btn_play_pause.isChecked():
            loc = mcon.get_loc("Start_Slideshow","Start Slideshow") 
            item = m.addAction(loc)
            # item.triggered.connect(lambda: preview_slideshow_switch.setChecked(True))
            item.triggered.connect(lambda: gl.btn_play_pause.setChecked(True)) 
        else:
            loc = mcon.get_loc("Pause_Slideshow","Pause Slideshow") 
            item = m.addAction(loc)
            # item.triggered.connect(lambda: preview_slideshow_switch.setChecked(False))
            item.triggered.connect(lambda: gl.btn_play_pause.setChecked(False))

        loc = mcon.get_loc("Pause_Slideshow","Pause Slideshow") 
        item = m.addAction(loc)
        item.triggered.connect(request_pause_slideshow)

        loc = mcon.get_loc("Keep_Media_Show","Pause Slideshow - Keep Media Show") 
        item = m.addAction(loc)
        item.triggered.connect(lambda: request_pause_slideshow(keep_media_show=True))

        loc = mcon.get_loc("Play_Next_Slideshow","Play Next - Slideshow") 
        item = m.addAction(loc)
        item.triggered.connect(request_play_next_slideshow)
        m.popup(QCursor.pos())


    # Context menu
    gl.preview_window.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    gl.preview_window.customContextMenuRequested.connect(show_context_menu_of_preview_window)


    def request_pause_slideshow(keep_media_show=False):
        nonlocal gl
        slideshow_profile["should_pause"] = True
        slideshow_profile["should_play_next"] = False
        if not keep_media_show:
            try:
                gl.preview_window.slideshow_media_window.stop_media_show()
            except Exception:
                pass


    def request_play_next_slideshow():
        nonlocal gl
        try:
            gl.preview_window.slideshow_media_window.stop_media_show()
        except Exception:
            pass
        slideshow_profile["should_play_next"] = True
        slideshow_profile["should_pause"] = False


        

    MARKED_TAG = "marked"
            

    def get_current_card():
        nonlocal gl
        if not gl.preview_window:
            return None
        try:
            return gl.preview_window.card()
        except TypeError:            
            return None # just in case the API changes
       


    def set_flag(flag_number: int):
        nonlocal browser
        card = get_current_card()
        if not card:
            return

        if 0 <= flag_number <= 7:
            # card.setUserFlag(flag_number)
            # mw.col.update_card(card)
            if browser:
                browser.set_flag_of_selected_cards(flag_number)



    def decrease_flag():
        nonlocal browser
        card = get_current_card()
        if not card:
            return

        current = card.userFlag()
        if current > 0:
            current = current - 1        
        # card.setUserFlag(current)
        # mw.col.update_card(card)
        if browser:
            browser.set_flag_of_selected_cards(current)


    def decrease_flag0():
        nonlocal browser
        card = get_current_card()
        if not card:
            return

        # card.setUserFlag(0)
        # mw.col.update_card(card)
        if browser:
            browser.set_flag_of_selected_cards(0)


    def increase_flag():
        nonlocal browser
        card = get_current_card()
        if not card:
            return

        current = card.userFlag()
        if current < 7:
            current = current + 1
        if browser:
            browser.set_flag_of_selected_cards(current)
        
        
    def get_current_card_and_note():
        nonlocal gl

        if not gl.preview_window:
            return None, None

        try:
            card = gl.preview_window.card()
        except TypeError:            
            card = None # just in case the API changes

        if not card:
            return None, None

        note = card.note()
        return card, note


   
    def change_star_button():
        nonlocal browser
        card, note = get_current_card_and_note()
        if not note:
            return

        if note.has_tag(MARKED_TAG):            
            if browser:
                browser.toggle_mark_of_selected_notes(checked=False)
        else:
            if browser:
                browser.toggle_mark_of_selected_notes(checked=True)
            

    def setup_preview_shortcuts(prev_window):
        # ⭐ Star
        QShortcut(
            QKeySequence("Ctrl+8"),
            prev_window,
            activated=change_star_button
        )    
        QShortcut(
            QKeySequence("Ctrl+K"),
            prev_window,
            activated=change_star_button
        )     
        QShortcut(
            QKeySequence("Insert"),
            prev_window,
            activated=change_star_button
        )     

        # 🚩 Flag0 / clear
        QShortcut(
            QKeySequence("Ctrl+0"),
            prev_window,
            activated=decrease_flag0
        )

        
        # 🚩 Flag down / cycle
        QShortcut(
            QKeySequence("Ctrl+-"),
            prev_window,
            activated=decrease_flag
        )

        # 🚩 Flag up / cycle
        QShortcut(
            QKeySequence("Ctrl+="),
            prev_window,
            activated=increase_flag
        )

        # 🚩 Direct flags Ctrl+1 .. Ctrl+7
        for i in range(1, 8):
            QShortcut(
                QKeySequence(f"Ctrl+{i}"),
                prev_window,
                activated=lambda i=i: set_flag(i)
                )
            
        QShortcut(
            QKeySequence("Alt+Left"),
            prev_window,
            activated=lambda: back_history()          
        )

        QShortcut(
            QKeySequence("Alt+Right"),
            prev_window,
            activated=lambda: forward_history()          
        )

        QShortcut(
            QKeySequence("R"),
           prev_window,
            activated=prev_window._on_replay_audio
        )

        QShortcut(
            QKeySequence("B"),
            prev_window,             
            activated=lambda: back_side_click()
        )

        QShortcut(
            QKeySequence("Ctrl+Home"),
            prev_window,
            activated=browser.onFirstCard
        )

        QShortcut(
            QKeySequence("Ctrl+End"),
            prev_window,
            activated=browser.onLastCard
        )

        QShortcut(
            QKeySequence("Up"),
            prev_window,
            activated=prev_window._on_prev
        )

        QShortcut(
            QKeySequence("Down"),
            prev_window,
            activated=prev_window._on_next
        )

        QShortcut(
            QKeySequence("F8"),
            prev_window,
            activated=lambda: f8_click()
        )        

        QShortcut(
            QKeySequence("F9"),
            prev_window,
            activated=lambda: f9_click()          
        )

        QShortcut(
            QKeySequence("F10"),
            prev_window,
            activated=request_play_next_slideshow          
        )
            
    setup_preview_shortcuts(gl.preview_window)  

    def back_side_click():        
        nonlocal gl
        gl.preview_window._on_show_both_sides( not gl.preview_window._show_both_sides )
        gl.btn_back_side.setChecked(gl.preview_window._show_both_sides)

    def f8_click():
        nonlocal gl
        set_slideshow_preview_sequence(not slideshow_profile["random_sequence"])
        gl.btn_random.setChecked(slideshow_profile["random_sequence"])

    def f9_click():
        nonlocal gl
        toggle_play_pause( not slideshow_profile["is_on"] )
        gl.btn_play_pause.setChecked(slideshow_profile["is_on"])

    def toggle_play_pause(checked):
        nonlocal gl
        if checked:
            gl.btn_play_pause.setIcon(gl.icon_pause)      
            gl.btn_step.setEnabled(True)
            gl.label_timer.setEnabled(True)                 
            on_switch_preview_slideshow(checked)  
        else:
            gl.btn_play_pause.setIcon(gl.icon_play)     
            gl.btn_step.setEnabled(False)
            gl.label_timer.setEnabled(False)                        
            on_switch_preview_slideshow(checked)  


    def stop_slideshow(source_object=None):
        global slideshow_profile 
        nonlocal gl

        slideshow_profile["is_on"] = False
        slideshow_profile["timeout"] = 0
        slideshow_profile["is_timeout_special"] = False
        slideshow_profile["special_timeout"] = 0
        slideshow_profile["is_showing_question"] = False
        slideshow_profile["showed_cards"] = []
        slideshow_profile["should_pause"] = False
        slideshow_profile["should_play_next"] = False

        # if preview_slideshow_switch and sip.isdeleted(preview_slideshow_switch) is False:
        #     loc1 = mcon.get_loc("Slideshow_On_Off","Slideshow On/Off")
        #     preview_slideshow_switch.setText(loc1)
        #     preview_slideshow_switch.setChecked(False)

        if  gl.label_timer and sip.isdeleted(gl.label_timer) is False:
            gl.label_timer.setText("0s")

        mplayer_extended.stop()
        try:
            gl.preview_window.slideshow_media_window.close()
        except Exception:
            pass
        logger.info("stopped slideshow")


    def on_switch_preview_slideshow(switch_state):
        global slideshow_profile
        nonlocal browser, gl 
        if not switch_state:
            if slideshow_profile["is_on"]:
                stop_slideshow()
            return

        slideshow_profile["should_play_next"] = False
        slideshow_profile["should_pause"] = False

        try:
            if not browser.isVisible() or not gl.preview_window.isVisible():
                return
        except Exception:
            return
        browser.destroyed.connect(stop_slideshow)
        gl.preview_window.destroyed.connect(stop_slideshow)
        c = browser.card
        if not c or not browser.singleCard:
            loc = mcon.get_loc("please_select_1_card","please select 1 card")
            show_text(f"{loc}.")
            stop_slideshow()
            return

        slideshow_profile["is_on"] = True
        slideshow_profile["should_pause"] = False
        slideshow_profile["should_play_next"] = False
        slideshow_preview_thread = SlideshowPreviewThread(slideshow_profile, browser, gl.preview_window)
        slideshow_preview_thread.signals.replay_audio_signal.connect(replay_audio)
        slideshow_preview_thread.signals.next_slide_signal.connect(turn_to_next_slide_preview)
        slideshow_preview_thread.signals.elapsed_time_signal.connect(update_preview_slideshow_switch_text)
        slideshow_preview_thread.signals.request_show_external_media_signal.connect(show_external_media)
        slideshow_preview_thread.signals.request_change_windows_stack_signal.connect(_arrange_windows_stack_sequence)
        thread_pool = QThreadPool.globalInstance()
        thread_pool.start(slideshow_preview_thread)
        logger.info("----------started preview slideshow thread----------")

        return


    def _arrange_windows_stack_sequence(name_of_widget_to_raise):
        nonlocal gl
        try:
            if name_of_widget_to_raise == "preview_window":
                gl.preview_window.raise_()
            if name_of_widget_to_raise == "slideshow_media_window":
                gl.preview_window.slideshow_media_window.raise_()
        except Exception:
            pass


    def show_external_media(path):
        global EXTERNAL_MEDIA_ROOT, slideshow_profile
        nonlocal browser, gl

        if path.startswith("$$"):
            path = path[2:]
        else:
            path = os.path.join(EXTERNAL_MEDIA_ROOT, path)
        # logger.debug("get rqt for ext media: %s" % path)
        if not path or not os.path.isfile(path) \
        or not any([path.lower().endswith(ext) for ext in MEDIAS + PICTURES]) \
        or not gl.preview_window or not browser:
            if not (gl.preview_window and browser):
                logger.debug("show ext media denied: no browser/preview_window")
            elif not (os.path.isfile(path)):
                logger.debug("show ext media denied: '%s' not existing" % path)
            elif not any([path.lower().endswith(ext) for ext in MEDIAS + PICTURES]):
                logger.debug("show ext media denied: '%s' not in ext %s" % (path, repr(MEDIAS + PICTURES)))
            slideshow_profile["show_external_media_event"].set()
            return
        global slideshow_media_window_area
        try:
            if not gl.preview_window.slideshow_media_window.isVisible():
                gl.preview_window.slideshow_media_window = SlideshowMediaWindow(gl.preview_window.parent(),
                                                                            slideshow_media_window_area)
                logger.info("started new slideshow media window")
        except Exception:
            gl.preview_window.slideshow_media_window = SlideshowMediaWindow(gl.preview_window.parent(),
                                                                        slideshow_media_window_area)
            logger.info("started new slideshow media window")
        try:
            if any([path.lower().endswith(ext) for ext in MEDIAS]):
                gl.preview_window.slideshow_media_window.show_video(path)
                logger.debug("sent ext medio play request %s" % path)
            else:
                gl.preview_window.slideshow_media_window.show_pic(path)
                logger.debug("sent ext pic show request %s" % path)
            if slideshow_profile["external_media_show_mode"] == "on_and_backoff_if_empty":
                if not any([path.lower().endswith(ext) for ext in AUDIOS]):
                    _arrange_windows_stack_sequence("slideshow_media_window")
                else:
                    _arrange_windows_stack_sequence("preview_window")
        except Exception:
            # don't care if external can't be showed correctly
            # though we hope it can
            pass
        slideshow_profile["show_external_media_event"].set()
        return



    def replay_audio(flag_replay_audio):
        global slideshow_profile
        nonlocal browser, gl

        if not flag_replay_audio:
            return
        
        try:
            if not browser.isVisible() or not gl.preview_window.isVisible():
                stop_slideshow()
                return
        except Exception:
            stop_slideshow()
            return
        if not slideshow_profile["is_on"]:
            return
        if app_version_micro() < 24:
            browser.mw.reviewer.replayAudio(browser)
        else:
            try:
                anki_replay_audio(
                    browser.card, slideshow_profile["is_showing_question"])
            except Exception as error:
                logger.debug('Replay Audio Error: ' + str(error))


    def turn_to_next_slide_preview(flag_go_next):
        global slideshow_profile
        nonlocal browser, gl
        if not flag_go_next:
            return        
        try:
            if not browser.isVisible() or not gl.preview_window.isVisible():
                stop_slideshow()
                return
        except Exception:
            stop_slideshow()
            return
        
        if not slideshow_profile["is_on"]:
            return
        
        #  can not use browser._previewState == "question", don't know why
        if slideshow_profile["is_showing_question"]:
            if app_version_micro() >= 24:
                gl.preview_window._on_next()
            else:
                browser._onPreviewNext()
            try:
                card = browser.card
                if card and browser.singleCard:
                    mw.addon_RTMD.relate_to_my_doc(card)
            except Exception as error:
                import traceback
                logger.debug(
                    'Fail to activate RelateToMyDoc plugin: '
                    + str(traceback.format_exc()))
        elif not slideshow_profile["random_sequence"]:
            if app_version_micro() >= 45:
                canForward = browser.table.has_next()
            else:
                canForward = browser.currentRow() < browser.model.rowCount(None) - 1
            if not not (browser.singleCard and canForward):
                if app_version_micro() >= 24:
                    gl.preview_window._on_next()
                else:
                    browser._onPreviewNext()
            else:
                stop_slideshow()
        else:
            if (
                (app_version_micro() >= 45
                and browser.table.len() <= 1)
                or
                (app_version_micro() < 45
                and len(browser.model.cards) <= 1)
            ):
                stop_slideshow()
                return

            # if all cards are showed, start like no card has been showed
            if app_version_micro() >= 45:
                rows_total = browser.table.len()
            else:
                rows_total = browser.model.rowCount(None)
            if len(slideshow_profile["showed_cards"]) >= rows_total:
                slideshow_profile["showed_cards"] = []
            # if version >= 45, slideshow_profile["showed_cards"] contains ids
            # else, it contains cards
            if app_version_micro() >= 45:
                pool = list(browser.table._model._items)
                pick = random.choice(list(
                    set(pool)
                    - set(slideshow_profile["showed_cards"])
                    ))
                new_row = pool.index(pick)
                slideshow_profile["showed_cards"].append(pick)
                browser.editor.call_after_note_saved(
                    lambda: browser.table._move_current_to_row(new_row))
            else:
                new_row = list(browser.model.cards).index(random.choice(list(
                    set(browser.model.cards)
                    - set(slideshow_profile["showed_cards"])
                    )))
                slideshow_profile["showed_cards"].append(browser.model.cards[new_row])
                browser.editor.saveNow(lambda: browser._moveCur(None, browser.model.index(new_row, 0)))
        # logger.debug("main thread seeing card " + browser.card._getQA()['q'])
        return


    def update_preview_slideshow_switch_text(elapsed_time):
        global slideshow_profile
        nonlocal gl
        if elapsed_time == -1:
            # wait for external media, maybe...
            count_down = "X"
        elif slideshow_profile["is_timeout_special"] and not slideshow_profile["is_showing_question"]:
            count_down = slideshow_profile["special_timeout"] - elapsed_time
        else:
            count_down = slideshow_profile["timeout"] - elapsed_time
    
        if count_down != "X" and count_down < 0:
            count_down = ""

        if gl.label_timer:
            try:            
                gl.label_timer.setText(f"%ss" % count_down)    
            except Exception as e:
                pass




    style = QApplication.style()
    icon_size = style.pixelMetric(QStyle.PixelMetric.PM_SmallIconSize)
    btn_size = icon_size + 6
    
    top_bar = QWidget()
    top_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    top_bar.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)
    top_bar.setFixedHeight(btn_size+2)     
    top_layout = QHBoxLayout(top_bar)    
    top_layout.setContentsMargins(1, 1, 1, 1)    
    top_layout.setSpacing(1)

    def mini_btn(
        text=None,
        icon=None,
        tooltip="",
        checkable=False        
    ):
        b = QPushButton()
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setCheckable(checkable)
        b.setFlat(True)
        b.setIconSize(QSize(icon_size, icon_size))
        b.setFixedSize(btn_size, btn_size)
        b.setToolTip(tooltip)
        if icon:
            b.setIcon(icon)            
        if text:
            b.setText(text)
        b.setContentsMargins(0, 0, 0, 0)    

        # b.setStyleSheet("""   
        # QPushButton {
        #     font-size: 11px;
        #     padding: 0px;
        #     border: none;
        # }
        # QPushButton:checked {
        #     background: rgba(255, 200, 0, 0.35);
        #     border-radius: 4px;
        # }
        # QPushButton:disabled {
        #     color: #888;
        # }
        # """)

        return b


    def back_history():
        nonlocal browser, gl
        prev_index = gl.history.back()    
        if prev_index is not None:      
            gl.history.ignore_1_add = True            
            browser.table._move_current_to_row(prev_index)       
        return prev_index


    def forward_history():
        nonlocal browser, gl
        next_index = gl.history.forward()    
        if next_index is not None:
            gl.history.ignore_1_add = True            
            browser.table._move_current_to_row(next_index)        
        return next_index


    def change_slideshow_setting():
        global config, external_media_show_mode_button, change_slideshow_setting_dialog, set_slideshow_q_time_button, set_slideshow_a_time_button   
        nonlocal browser, gl
        change_slideshow_setting_dialog = QDialog(gl.preview_window)
        loc = mcon.get_loc("Preview_Slideshow_Setting","Preview Slideshow Setting")
        change_slideshow_setting_dialog.setWindowTitle(loc)
        layout = QVBoxLayout()

        if mcon.key_in_gs("preview_slideshow_show_question_time"):
            q_time = mcon.get_gs("preview_slideshow_show_question_time")
            try:
                q_time = int(q_time)
            except Exception:
                q_time = 3
            if q_time < 1:
                q_time = 3
            if q_time != mcon.get_gs("preview_slideshow_show_question_time"):
                mcon.set_gs("preview_slideshow_show_question_time", q_time)            
        else:
            q_time = 3
            mcon.set_gs("preview_slideshow_show_question_time", 3)        
        slideshow_profile["q_time"] = q_time
        
        loc = mcon.get_loc("Set_Question_Time","Set Question Time")
        set_slideshow_q_time_button = QPushButton(f"{loc} (%ss)" % q_time)
        loc = mcon.get_loc("Set_Question_Time_ToolTip","Set the time displaying question")
        set_slideshow_q_time_button.setToolTip(loc)
        set_slideshow_q_time_button.clicked.connect(set_preview_slideshow_question_time)

        # show_text(repr(mcon.get_gs("preview_slideshow_show_answer_time")))
        if mcon.key_in_gs("preview_slideshow_show_answer_time"):
            a_time = mcon.get_gs("preview_slideshow_show_answer_time")
            try:
                a_time = int(a_time)
            except Exception:
                a_time = 5
            if a_time < 1:
                a_time = 5
            if a_time != mcon.get_gs("preview_slideshow_show_answer_time"):
                mcon.set_gs("preview_slideshow_show_answer_time", a_time)            
        else:
            a_time = 5
            mcon.set_gs("preview_slideshow_show_answer_time", 5)        
        slideshow_profile["a_time"] = a_time
        
        loc = mcon.get_loc("Set_Answer_Time","Set Answer Time")
        set_slideshow_a_time_button = QPushButton(f"{loc} (%ss)" % a_time)    
        loc = mcon.get_loc("Set_Answer_Time_ToolTip","Set the time displaying answer")
        set_slideshow_a_time_button.setToolTip(loc)
        set_slideshow_a_time_button.clicked.connect(set_preview_slideshow_answer_time)

        # external_media_show_mode
        # below line is required, otherwise ref is missing
        
        if mcon.key_in_gs("external_media_show_mode"):
            external_media_show_mode = mcon.get_gs("external_media_show_mode")
            if external_media_show_mode not in ["off",
                                                "on",
                                                "on_and_backoff_if_empty"]:
                external_media_show_mode = "on"
        else:
            external_media_show_mode = "on"
        slideshow_profile["external_media_show_mode"] = external_media_show_mode
        if not mcon.key_in_gs("external_media_show_mode") \
        or mcon.get_gs("external_media_show_mode") != external_media_show_mode:
            mcon.set_gs("external_media_show_mode", external_media_show_mode)        
        if external_media_show_mode == "on_and_backoff_if_empty":
            external_media_show_mode_button_text = "\n" + external_media_show_mode.capitalize()
        else:
            external_media_show_mode_button_text = external_media_show_mode.capitalize()
        loc = mcon.get_loc("External_Media_Show_Mode","External Media Show Mode")
        external_media_show_mode_button = QPushButton(f"{loc}: %s" % external_media_show_mode_button_text)
        loc = mcon.get_loc("Loop_through_setting", "Loop through setting on how to show external media:\n"
                                                "'off' - ignore any exteral media\n"
                                                "'on' - show external media window after first exteral media found\n"
                                                "'on_and_backoff_if_empty' - show external media window if any, \n"
                                                "but bring up preview window if external media field is empty.")
        external_media_show_mode_button.setToolTip(loc)

        def change_external_media_show_mode():       
            global config 
            if slideshow_profile["external_media_show_mode"] == "off":
                external_media_show_mode = "on"
            if slideshow_profile["external_media_show_mode"] == "on":
                external_media_show_mode = "on_and_backoff_if_empty"
            if slideshow_profile["external_media_show_mode"] == "on_and_backoff_if_empty":
                external_media_show_mode = "off"
            slideshow_profile["external_media_show_mode"] = external_media_show_mode
            
            if not mcon.key_in_gs("external_media_show_mode") \
            or mcon.get_gs("external_media_show_mode") != external_media_show_mode:
                mcon.set_gs("external_media_show_mode", external_media_show_mode)            
            if external_media_show_mode == "on_and_backoff_if_empty":
                external_media_show_mode_button_text = "\n" + external_media_show_mode.capitalize()
            else:
                external_media_show_mode_button_text = external_media_show_mode.capitalize()
            loc = mcon.get_loc("External_Media_Show_Mode","External Media Show Mode")  
            external_media_show_mode_button.setText(f"{loc}: %s" % external_media_show_mode_button_text)
        external_media_show_mode_button.clicked.connect(change_external_media_show_mode)

        loc = mcon.get_loc("Set_External_Media_Folder_Root","Set External Media Folder Root")  
        set_external_media_folder_button = QPushButton(loc)
        loc = mcon.get_loc("Set_External_Media_Folder_Root_ToolTip","Select root folder for external media. When set, relative path can be use in 'Slideshow_External_Media' field")
        set_external_media_folder_button.setToolTip(loc)
        set_external_media_folder_button.clicked.connect(change_external_media_folder)

        loc = mcon.get_loc("Set_External_Media_Volume","Set External Media Volume")  
        set_external_media_volume_button = QPushButton(loc)
        loc = mcon.get_loc("Set_External_Media_Volume_ToolTip","Set External Media Volume.\nEffective after external media window restarted.")
        set_external_media_volume_button.setToolTip(loc)

        def set_external_media_volume():
            global change_slideshow_setting_dialog
            volume_control = ExternalMediaVolumeControlSlider(change_slideshow_setting_dialog)
            volume_control.show()
        set_external_media_volume_button.clicked.connect(set_external_media_volume)

        loc = mcon.get_loc("Show_Instruction","Show Instruction")  
        show_instruction_button = QPushButton(loc)
            
        loc = mcon.get_loc("INSTRUCTIONS", "")  
        if loc:
            loc = "\n".join(loc) 
        else:
            loc = INSTRUCTIONS

        placeholders = {
            "Slideshow_On_Off": mcon.get_loc("Slideshow_On_Off", "Slideshow On/Off"),
            "Random_Seq": mcon.get_loc("Random_Seq", "Random Seq")
        }    
        loc = loc.format_map(placeholders)
        # show_instruction_button.clicked.connect(lambda: show_text(loc))
        show_instruction_button.clicked.connect( lambda: show_simple_instruction(gl.preview_window, loc) )

        layout.addWidget(set_slideshow_q_time_button)
        layout.addWidget(set_slideshow_a_time_button)
        layout.addWidget(external_media_show_mode_button)
        layout.addWidget(set_external_media_folder_button)
        layout.addWidget(set_external_media_volume_button)
        layout.addWidget(show_instruction_button)

        layout.addStretch()

        add_shige_buttons(layout)

        change_slideshow_setting_dialog.setLayout(layout)
        change_slideshow_setting_dialog.exec()



    top_layout.addStretch()
    top_layout.addSpacing(2)
    
    loc = mcon.get_loc("Back_history", "Back (history)")
    gl.btn_back = mini_btn("⭠", tooltip=f"{loc} [Alt+←]")
    gl.btn_back.setEnabled(True)
    gl.btn_back.clicked.connect(back_history)
    top_layout.addWidget(gl.btn_back)
    
    loc = mcon.get_loc("Forward_history", "Forward (history)")
    gl.btn_forward = mini_btn("⭢", tooltip=f"{loc} [Alt+→]")
    gl.btn_forward.setEnabled(True)
    gl.btn_forward.clicked.connect(forward_history)
    top_layout.addWidget(gl.btn_forward)

    top_layout.addSpacing(3)

    loc = mcon.get_loc("Repeat_audio", "Repeat audio")
    gl.btn_repeat = mini_btn("🔊", tooltip=f"{loc} [R]")
    top_layout.addWidget(gl.btn_repeat)
    gl.btn_repeat.clicked.connect(gl.preview_window._on_replay_audio)

    loc = mcon.get_loc("Back_side_only", "Back side only")
    gl.btn_back_side = mini_btn("🄱", tooltip=f"{loc} [B]", checkable=True)
    top_layout.addWidget(gl.btn_back_side)
    gl.btn_back_side.setChecked(gl.preview_window._show_both_sides)
    gl.btn_back_side.toggled.connect(gl.preview_window._on_show_both_sides)
    
    top_layout.addSpacing(3)
    
    loc = mcon.get_loc("To_the_beginning_list", "To the beginning of the list")
    btn_First = mini_btn("⤒", tooltip=f"{loc} [Ctrl+Home]")
    top_layout.addWidget(btn_First)
    btn_First.clicked.connect(browser.onFirstCard)

    loc = mcon.get_loc("Previous_card", "Previous card")
    gl.btn_prev = mini_btn("▲", tooltip=f"{loc} [Up]")
    top_layout.addWidget(gl.btn_prev)
    gl.btn_prev.clicked.connect(gl.preview_window._on_prev)
    
    loc = mcon.get_loc("Next_card", "Next card")
    gl.btn_next = mini_btn("▼", tooltip=f"{loc} [Down]")
    top_layout.addWidget(gl.btn_next)    
    gl.btn_next.clicked.connect(gl.preview_window._on_next)

    loc = mcon.get_loc("To_the_end_list", "To the end of the list")
    btn_Last = mini_btn("⤓", tooltip=f"{loc} [Ctrl+End]")
    top_layout.addWidget(btn_Last)
    btn_Last.clicked.connect(browser.onLastCard)

    top_layout.addSpacing(3)

    loc = mcon.get_loc("Slideshow_Setting_ToolTip","Change Slideshow Settings") 
    btn_settings = mini_btn("⚙", tooltip=loc)
    btn_settings.clicked.connect(change_slideshow_setting)
    top_layout.addWidget(btn_settings)

    top_layout.addSpacing(3)    

    btn_star = mini_btn("★", tooltip="[Ctrl+8] / [Ctrl+K] / [Insert]")
    btn_star.clicked.connect(change_star_button)    
    top_layout.addWidget(btn_star)

    btn_flag_minus = mini_btn("−⚑", tooltip="[Ctrl+-] / [Ctrl+0]-off")
    btn_flag_minus.clicked.connect(decrease_flag)    
    top_layout.addWidget(btn_flag_minus)

    btn_flag_plus = mini_btn("+⚑", tooltip="[Ctrl+=] / [Ctrl+1]...[Ctrl+7]")
    btn_flag_plus.clicked.connect(increase_flag)
    top_layout.addWidget(btn_flag_plus)

    top_layout.addSpacing(3)

    loc = mcon.get_loc("Shuffle", "Shuffle")
    gl.btn_random = mini_btn("🔀", tooltip=f"{loc} [F8]", checkable=True)
    gl.btn_random.setChecked(slideshow_profile["random_sequence"])
    gl.btn_random.toggled.connect(set_slideshow_preview_sequence)
    top_layout.addWidget(gl.btn_random)


    style = gl.preview_window.style()
    gl.icon_play = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
    gl.icon_pause = style.standardIcon(QStyle.StandardPixmap.SP_MediaPause)
    icon_step = style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward)

    loc = mcon.get_loc("Start_Pause", "Start / Pause")
    gl.btn_play_pause = mini_btn(icon=gl.icon_play, tooltip=f"{loc} [F9]", checkable=True ) 
           
    gl.btn_play_pause.toggled.connect(toggle_play_pause)
    top_layout.addWidget(gl.btn_play_pause)

    loc = mcon.get_loc("Show_Next_Slide_ToolTip","Show Next Slide")
    gl.btn_step = mini_btn(icon=icon_step, tooltip=f"{loc} [F10]")     
    gl.btn_step.setEnabled(False)
    gl.btn_step.clicked.connect(request_play_next_slideshow)
    top_layout.addWidget(gl.btn_step)    

    top_layout.addSpacing(3)

    gl.label_timer = QLabel("0s")    
    top_layout.addWidget(gl.label_timer) 


    def toggle_on_top(checked):
        global config
        nonlocal gl
        gl.preview_window.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            checked
        )
        try:
            mcon.set_gs("WindowStaysOnTop", "1" if checked else "")            
        except:
            pass
        gl.preview_window.show()
       
    loc = mcon.get_loc("On_top_of_all_windows", "On top of all windows")
    btn_pin = mini_btn("📌", tooltip=loc, checkable=True)
    top_layout.addStretch()
    top_layout.addSpacing(2)
    top_layout.addWidget(btn_pin, 0, Qt.AlignmentFlag.AlignVCenter)      
    btn_pin.toggled.connect(toggle_on_top)

    try:
        WindowStaysOnTop = ""
        if mcon.key_in_gs("WindowStaysOnTop"):
            WindowStaysOnTop = mcon.get_gs("WindowStaysOnTop")
        is_on = WindowStaysOnTop.lower() in ("1", "on", "true")
        btn_pin.setChecked(is_on)
        toggle_on_top(is_on)
    except:
        pass 


    layout = gl.preview_window.layout()
    if layout:
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.insertWidget(0, top_bar)
    else:
        layout = QVBoxLayout(gl.preview_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        gl.preview_window.setLayout(layout)
        layout.insertWidget(0, top_bar)    


    gl.preview_window._updateButtons()


 







class ExternalMediaVolumeControlSlider(QSlider):

    def __init__(self, parent, *args, **kwargs):
        global config
        super().__init__(Qt.Orientation.Horizontal, parent, *args, **kwargs)
        self.setMinimum(0)
        self.setMaximum(100)        
        try:
            self.volume = int(mcon.get_gs("mplayer_startup_volume"))
        except Exception:
            self.volume = 50
        if self.volume < 0 or self.volume > 100:
            self.volume = 50
        self.setValue(self.volume)
        loc = mcon.get_loc("Current","Current") 
        self.setToolTip(f"{loc} - %s%%" % self.volume)
        self.valueChanged.connect(self.set_volume)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window | Qt.WindowType.Popup)
        self.setStyleSheet("border:1px solid grey;")
        self.move(QCursor.pos().x() - self.width(), QCursor.pos().y())

    def set_volume(self, volume):
        self.volume = volume
        mcon.set_gs_ns("mplayer_startup_volume", volume) 
        loc = mcon.get_loc("Current","Current") 
        self.setToolTip(f"{loc} - %s%%" % volume)
        QToolTip.showText(QCursor.pos(), "%s%%" % volume, self)


    def mousePressEvent(self, event):
        if pyqt_version == "PyQt6":
            if int(event.globalPosition().x()) < self.x() \
            or int(event.globalPosition().x()) > self.x() + self.frameGeometry().width() \
            or int(event.globalPosition().y()) < self.y() \
            or int(event.globalPosition().y()) > self.y() + self.frameGeometry().height():
                self.close()            
        else:
            if event.globalX() < self.x() \
            or event.globalX() > self.x() + self.frameGeometry().width() \
            or event.globalY() < self.y() \
            or event.globalY() > self.y() + self.frameGeometry().height():
                self.close()
        super().mousePressEvent(event)

    def closeEvent(self, event):
        mcon.write_config(config)        
        logger.debug("External Media Volume Set to %s" % self.volume)
        super().closeEvent(event)



def set_preview_slideshow_question_time():
    loc1 = mcon.get_loc("Change_Question_Displaying_Time","Change Question Displaying Time")
    loc2 = mcon.get_loc("Input_question_displaying_time","Input question displaying time in seconds")
    new_q_time, is_ok = QInputDialog.getInt(change_slideshow_setting_dialog,
                                            loc1,
                                            loc2,
                                            value=slideshow_profile["q_time"],
                                            min=1,
                                            max=60 * 60,
                                            step=1)
    q_time = slideshow_profile["q_time"]
    global set_slideshow_q_time_button, config 
    if is_ok:
        if new_q_time != q_time:
            q_time = new_q_time            
            mcon.set_gs("preview_slideshow_show_question_time", q_time)            
            loc = mcon.get_loc("Set_Question_Time","Set Question Time") 
            set_slideshow_q_time_button.setText(f"{loc} (%ss)" % q_time)
            slideshow_profile["q_time"] = q_time


def set_preview_slideshow_answer_time():
    loc1 = mcon.get_loc("Change_Answer_Displaying_Time","Change Answer Displaying Time")
    loc2 = mcon.get_loc("Input_answer_displaying_time","Input answer displaying time in seconds")
    new_a_time, is_ok = QInputDialog.getInt(change_slideshow_setting_dialog,
                                            loc1,
                                            loc2,
                                            value=slideshow_profile["a_time"],
                                            min=1,
                                            max=60 * 60,
                                            step=1)
    a_time = slideshow_profile["a_time"]
    global set_slideshow_a_time_button, config
    if is_ok:
        if new_a_time != a_time:
            a_time = new_a_time            
            mcon.set_gs("preview_slideshow_show_answer_time", a_time)            
            loc = mcon.get_loc("Set_Answer_Time","Set Answer Time") 
            set_slideshow_a_time_button.setText(f"{loc} (%ss)" % a_time)
            slideshow_profile["a_time"] = a_time


def change_external_media_folder():
    global config
    if mcon.key_in_gs("external_media_folder_path"):
        path = mcon.get_gs("external_media_folder_path")
        if not os.path.isdir(path):
            path = ""
    else:
        path = ""
    loc = mcon.get_loc("Set_External_Media_Folder_Root","Set External Media Folder Root")     
    new_path = QFileDialog.getExistingDirectory(change_slideshow_setting_dialog,
                                                loc,
                                                path,
                                                QFileDialog.Option.ShowDirsOnly
                                                | QFileDialog.Option.DontResolveSymlinks)
    if not os.path.isdir(new_path):
        return
    else:
        loc = mcon.get_loc("External_media_folder_root_set_to","External media folder root set to")
        show_text(f"{loc}:\n" + new_path)
        mcon.set_gs("external_media_folder_path", new_path)        
        global EXTERNAL_MEDIA_ROOT
        EXTERNAL_MEDIA_ROOT = new_path





def set_slideshow_preview_sequence(state):
    global slideshow_profile
    if state:
        slideshow_profile["random_sequence"] = True
    else:
        slideshow_profile["random_sequence"] = False

       




# def dev_debug():
#     from aqt import QListWidget,Qt
#     # from PyQt5.QtWidgets import QListWidget
#     # from PyQt5.QtCore import Qt

#     debug_actions = {}

#     def close_media_window():
#         gl.preview_window.slideshow_media_window.stop_media_show()
#         gl.preview_window.slideshow_media_window.close()
#     debug_actions["close_media_window"] = close_media_window

#     def play_mp4():
#         path = r"d:\Downloads\InstaDown\45164780_311995036059669_6665285820453537716_n.mp4"
#         show_external_media(path)
#     debug_actions["play_mp4"] = play_mp4

#     def show_pic():
#         show_external_media(r"tumblr_p5nc3j7HyR1vlrtooo1_540.jpg")
#     debug_actions["show_pic"] = show_pic

#     debug_choices = QListWidget(gl.preview_window)
#     debug_choices.setWindowFlags(Qt.WindowType.Window)
#     for action_name in debug_actions:
#         debug_choices.addItem(action_name)
#         debug_choices.itemDoubleClicked.connect(lambda item: debug_actions[item.text()]())
#     debug_choices.show()

# Copyright (C) tosimplicity 2019-2021 <https://github.com/tosimplicity>
# Copyright (C) Shigeyuki 2024-2025 <http://patreon.com/Shigeyuki>
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

import logging
import threading

from aqt import QDialog, QMenu
from aqt import QPixmap
from aqt import QMovie, QCursor
from aqt import Qt, QByteArray
from aqt import mw

# Take low-level Qt classes (layout engine) like this:
try:
    from PyQt6.QtWidgets import QFrame, QStyle, QLabel, QHBoxLayout, QVBoxLayout, QLayout, QWidgetItem, QSpacerItem, QSizePolicy, QDialogButtonBox
    from PyQt6.QtCore import QRect, QPoint, QSize
    from PyQt6.QtGui import QShortcut, QKeySequence, QKeyEvent
    pyqt_version = "PyQt6"
except ImportError:
    from PyQt5.QtWidgets import QFrame, QStyle, QLabel, QHBoxLayout, QVBoxLayout, QLayout, QWidgetItem, QSpacerItem, QSizePolicy, QDialogButtonBox
    from PyQt5.QtCore import QRect, QPoint, QSize
    from PyQ5.QtGui import QShortcut, QKeySequence, QKeyEvent
    pyqt_version = "PyQt5"

from . import mplayer_extended
from . import config_addon as mcon

logger = logging.getLogger(__name__)



class SlideshowMediaWindow(QDialog):

    def __init__(self, parent, area=None, *args, **kwargs):        
        "parent: parent widget"
        "area: top-left-x(to screen), top-left-y(to screen), width, height"
        super(SlideshowMediaWindow, self).__init__(parent, *args, **kwargs)
        self.setWindowTitle("Slideshow External Media Window")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setSizePolicy(sizePolicy)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, on=True)
        # self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        # self.setWindowFlags( Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint )
        # 20260101 StaysOnTop 
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint 
        checked = False
        try:       
            MPlayerStaysOnTop = ""            
            if mcon.key_in_gs("MPlayerStaysOnTop"):
                MPlayerStaysOnTop = mcon.get_gs("MPlayerStaysOnTop")
            checked = MPlayerStaysOnTop.lower() in ("1", "on", "true")
        except:
            pass
        if checked:
            flags |= Qt.WindowType.WindowStaysOnTopHint 
        self.setWindowFlags(flags)

        self.setSizeGripEnabled(True)

        self.layout = QVBoxLayout()
        self.media_container = QLabel(self)
        self.media_container.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, on=True)
        # self.media_container.setFrameShape(QFrame.NoFrame)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        sizePolicy.setHeightForWidth(self.media_container.sizePolicy().hasHeightForWidth())
        self.media_container.setSizePolicy(sizePolicy)
        self.media_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_container.setStyleSheet("background-color: black;")

        self.layout.addWidget(self.media_container)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.setLayout(self.layout)
        self.area = area
        if any(area):
            self.resize(area[2], area[3])
            self.move(area[0], area[1])
        else:
            self.resize(400, 300)
        self.mouse_pos = [0, 0]
        self.allow_resize_mouse_press = False

        self.pic_image = None
        self.media_container.setScaledContents(False)
        self.media_container.original_resizeEvent = self.media_container.resizeEvent

        def media_container_resizeEvent(event):
            if self.pic_image and isinstance(self.pic_image, QPixmap):
                if self.pic_image.width() > self.media_container.width() - 2 \
                   and self.pic_image.height() > self.media_container.height() - 2:
                    target_width = self.media_container.width() - 2
                    target_height = self.media_container.height() - 2
                else:
                    target_width = self.pic_image.width()
                    target_height = self.pic_image.height()
                scaled_image = self.pic_image.scaled(target_width,
                                                     target_height,
                                                     aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                                                     transformMode=Qt.TransformationMode.FastTransformation)
                self.media_container.setPixmap(scaled_image)
            elif self.pic_image and isinstance(self.pic_image, QMovie):
                if self.pic_image.original_size.width() > self.media_container.width() - 2 \
                   and self.pic_image.original_size.height() > self.media_container.height() - 2:
                    target_width = self.media_container.width() - 2
                    target_height = self.media_container.height() - 2
                else:
                    target_width = self.pic_image.original_size.width()
                    target_height = self.pic_image.original_size.height()
                scaled_size = self.pic_image.original_size.scaled(target_width, target_height, Qt.AspectRatioMode.KeepAspectRatio)
                self.pic_image.setScaledSize(scaled_size)
            else:
                self.media_container.original_resizeEvent(event)
        self.media_container.resizeEvent = media_container_resizeEvent

        self.show()

        self.last_media_path = ""
        self.media_show_completed_notice = None
        # this should be a function to be called like self.stop_media_show()
        self.stop_media_show = lambda: None

        self.gif_completed_notice = threading.Event()


    

    def show_video(self, path):
        self.stop_media_show()
        self.media_container.clear()
        # some say the winId change all the time...so...
        mplayer_extended.setup(int(self.media_container.winId()))
        self.media_show_completed_notice = mplayer_extended.play(path)
        logger.debug("ext-media-win showed video: %s" % path)
        self.last_media_path = path
        self.stop_media_show = mplayer_extended.stop

    def show_pic(self, path):
        self.stop_media_show()
        self.media_container.clear()
        if not path.lower().endswith(".gif"):
            self.pic_image = QPixmap(path)
            if self.pic_image.width() > self.media_container.width() - 2 \
               and self.pic_image.height() > self.media_container.height() - 2:
                target_width = self.media_container.width() - 2
                target_height = self.media_container.height() - 2
            else:
                target_width = self.pic_image.width()
                target_height = self.pic_image.height()
            scaled_image = self.pic_image.scaled(target_width,
                                                 target_height,
                                                 aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                                                 transformMode=Qt.TransformationMode.SmoothTransformation)
            self.media_container.setPixmap(scaled_image)
            logger.debug("ext-media-win showed pic: %s" % path)
            self.stop_media_show = lambda: None
            self.media_show_completed_notice = None
        else:
            self.last_media_path = path
            self.pic_image = QMovie(path, QByteArray(), self)
            if not self.pic_image.isValid():
                self.media_show_completed_notice = None
                return
            self.pic_image.setCacheMode(QMovie.CacheMode.CacheAll)
            self.pic_image.jumpToNextFrame()
            self.pic_image.original_size = self.pic_image.currentPixmap().size()
            if self.pic_image.original_size.width() > self.media_container.width() - 2 \
               and self.pic_image.original_size.height() > self.media_container.height() - 2:
                target_width = self.media_container.width() - 2
                target_height = self.media_container.height() - 2
            else:
                target_width = self.pic_image.original_size.width()
                target_height = self.pic_image.original_size.height()
            scaled_size = self.pic_image.original_size.scaled(target_width, target_height, Qt.AspectRatioMode.KeepAspectRatio)
            self.pic_image.setScaledSize(scaled_size)
            self.pic_image.setSpeed(100)
            self.media_container.setMovie(self.pic_image)

            self.media_show_completed_notice = self.gif_completed_notice
            self.media_show_completed_notice.clear()

            def frameChanged_Handler(frameNumber):
                if frameNumber >= self.pic_image.frameCount() - 1:
                    self.pic_image.stop()
                    self.media_show_completed_notice.set()
            self.pic_image.frameChanged.connect(frameChanged_Handler)
            self.pic_image.start()
            logger.debug("ext-media-win showed gif: %s" % path)

            def stop_gif():
                try:
                    self.pic_image.stop()
                    self.media_show_completed_notice.set()
                except Exception:
                    pass
            self.stop_media_show = stop_gif

    def contextMenuEvent(self, event):        
        m = QMenu(self)
        loc = mcon.get_loc("Always_on_top", "Always on top")
        item = m.addAction(f"{loc} [Ctrl+A]")
        item.setCheckable(True)
        checked = False
        try:       
            MPlayerStaysOnTop = ""            
            if mcon.key_in_gs("MPlayerStaysOnTop"):
                MPlayerStaysOnTop = mcon.get_gs("MPlayerStaysOnTop")
            checked = MPlayerStaysOnTop.lower() in ("1", "on", "true")
        except:
            pass
        item.setChecked(checked)
        item.triggered.connect(self.toggle_on_top)

        loc = mcon.get_loc("Pause", "Pause")
        item = m.addAction(f"{loc} [Space]")
        item.triggered.connect(self.toggle_pause)
        loc = mcon.get_loc("Stop_Media", "Stop Media")
        item = m.addAction(loc)
        item.triggered.connect(self.stop_media_show)
        loc = mcon.get_loc("Exit_Media_Window", "Exit Media Window")
        item = m.addAction(f"{loc} [Esc]")
        item.triggered.connect(self.close)
        item = m.addSeparator()
        item = m.addAction("(🔊:⮃   •▶•:⮂ 1s +Ctrl=5s")
        item = m.addAction(" +Shift=10s+Ctrl=30s Alt-min)")
        m.popup(QCursor.pos())

    

    DRAG_ZONE_RATIO = 0.15      # 15% above
    DRAG_THRESHOLD = 4          # px — to distinguish a click from a drag

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        pos = event.position()
        self._press_pos = pos
        self._press_global = event.globalPosition()
        self._dragging = False

        h = self.height()
        self._in_drag_zone = pos.y() <= h * self.DRAG_ZONE_RATIO

        event.accept()


    def mouseMoveEvent(self, event):
        if not hasattr(self, "_press_pos"):
            return super().mouseMoveEvent(event)

        if not self._in_drag_zone:
            return

        delta = event.globalPosition() - self._press_global

        if not self._dragging:
            if delta.manhattanLength() < self.DRAG_THRESHOLD:
                return
            self._dragging = True

        self.move(
            int(self.x() + delta.x()),
            int(self.y() + delta.y())
        )

        self._press_global = event.globalPosition()
        event.accept()


    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)

        # If there was NO drag and click NOT in the top zone → pause
        if not self._dragging and not self._in_drag_zone:
            self.toggle_pause()

        self._dragging = False
        event.accept()
    

   

    
    def mouseDoubleClickEvent(self, event):
        self.setWindowState(self.windowState() ^ Qt.WindowState.WindowFullScreen)
        super().mouseDoubleClickEvent(event)

    def toggle_on_top(self, checked):              
        try:
            flags = self.windowFlags()
            if checked:
                flags |= Qt.WindowType.WindowStaysOnTopHint
            else:
                flags &= ~Qt.WindowType.WindowStaysOnTopHint       
            self.setWindowFlags(flags)             
            mcon.set_gs("MPlayerStaysOnTop", "1" if checked else "")                        
            self.show()
        except:
            pass


        



    def keyPressEvent(self, event):        
        key = event.key()
        mods = event.modifiers()
        if event.key() == Qt.Key.Key_Period:
            self.stop_media_show()
            return
        if event.key() == Qt.Key.Key_F11:
            self.setWindowState(self.windowState() ^ Qt.WindowState.WindowFullScreen)
            return
        if event.key() == Qt.Key.Key_Escape:                
            self.close()
            return
        if event.key() == Qt.Key.Key_Space:
            self.toggle_pause()
            return
        
        if event.key() == Qt.Key.Key_Up:
            self.volume_change(5)
            return
        
        if event.key() == Qt.Key.Key_Down:
            self.volume_change(-5)
            return
        
        if event.key() == Qt.Key.Key_A:
            ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
            if ctrl:                               
                checked = False
                try:       
                    MPlayerStaysOnTop = ""            
                    if mcon.key_in_gs("MPlayerStaysOnTop"):
                        MPlayerStaysOnTop = mcon.get_gs("MPlayerStaysOnTop")
                    checked = MPlayerStaysOnTop.lower() in ("1", "on", "true")
                except:
                    pass
                
                self.toggle_on_top(not checked)                
            return

        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            direction = 1 if key == Qt.Key.Key_Right else -1

            alt = bool(mods & Qt.KeyboardModifier.AltModifier)
            ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
            shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)

            if alt: # min                
                if ctrl and shift:
                    step = 30 * 60
                elif shift:
                    step = 10 * 60
                elif ctrl:
                    step = 5 * 60
                else:
                    step = 1 * 60
            else: # sec                
                if ctrl and shift:
                    step = 30
                elif shift:
                    step = 10
                elif ctrl:
                    step = 5
                else:
                    step = 1

            self.seek(direction * step)
            return

        
        super().keyPressEvent(event)




    def toggle_pause(self):
        if mplayer_extended:
            try:
                mplayer_extended.pause()
            except:
                pass

    def seek(self, sec : int):
        if mplayer_extended:
            try:
                mplayer_extended.seek(sec)
            except:
                pass

    def volume_change(self, delta : int):
        if mplayer_extended:
            try:
                mplayer_extended.volume_change(delta)
            except:
                pass

            
    


    def closeEvent(self, event):
        self.stop_media_show()
        self.area[0] = self.x()
        self.area[1] = self.y()
        self.area[2] = self.width()
        self.area[3] = self.height()
        event.accept()

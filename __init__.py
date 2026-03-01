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

__version__ = "0.9"
__license__ = "GNU Affero General Public License, version 3 or later"

import logging

from aqt import mw, appVersion

from .logging_handlers import TimedRotatingFileHandler
from .utils import get_path, app_version_micro
from .main import setup_preview_slideshow
# from .main import previewer_init

from anki.utils import pointVersion as app_version_micro

from .shige_config.popup_config import set_gui_hook_change_log
set_gui_hook_change_log()

logger = logging.getLogger(__name__)
f_handler = TimedRotatingFileHandler(
    get_path("addon_log"), when='D', interval=7, backupCount=1, encoding="utf-8")
f_handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d-%(module)20s-%(levelname)5s>> %(message)s",
                                         "%y%m%d %H%M%S"))
f_handler.setLevel(logging.DEBUG)
logger.addHandler(f_handler)
config = mw.addonManager.getConfig(__name__)
if config.get("debug", False):
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
logger.info("\n" * 3 + " - Start Add-on - " + "\n" * 2)

if app_version_micro() >= 20:
    # using new style hook
    logger.info("Anki version = " + appVersion)
    from aqt import gui_hooks
    gui_hooks.browser_menus_did_init.append(setup_preview_slideshow)
    # gui_hooks.card_review_webview_did_init.append(previewer_init)
else:
    # legacy
    # runHook('browser.setupMenus', self)
    from anki.hooks import addHook
    addHook('browser.setupMenus', setup_preview_slideshow)


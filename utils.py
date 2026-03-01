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

import os.path
import sys
import locale
import logging


from aqt import mw
from aqt.qt import QMessageBox

# from aqt import mw, appVersion
# app_version_micro = int(appVersion.rsplit('.', 1)[-1])
from anki.utils import pointVersion as app_version_micro


def get_path(*args):

    path = mw.addonManager.addonsFolder(__name__.split(".")[0])
    for item in args:
        path = os.path.join(path, str(item).strip())
    return path

def show_text(text):

    result = QMessageBox(QMessageBox.Icon.Information, "Information:", text).exec()
    return result

def log(*args):
    return logging.getLogger(__name__).info(*args)


def decode_sp(message, encoding=""):
    'special decoding, will also try coding:\n'
    '"utf-8", sys.stdout.encoding, locale.getpreferredencoding(), sys.getdefaultencoding()'
    try:
        if encoding:
            message_decoded = message.decode(encoding)
    except UnicodeDecodeError:
        pass
    try:
        message_decoded = message.decode("utf-8")
    except UnicodeDecodeError:
        try:
            message_decoded = message.decode(sys.stdout.encoding)
        except UnicodeDecodeError:
            try:
                message_decoded = message.decode(locale.getpreferredencoding())
            except UnicodeDecodeError:
                message_decoded = message.decode(sys.getdefaultencoding())
    return message_decoded


if __name__ == "__main__":
    pass

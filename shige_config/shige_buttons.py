# Copyright (C) Shigeyuki <http://patreon.com/Shigeyuki>
# License: GNU AGPL version 3 or later <http://www.gnu.org/licenses/agpl.html>

from aqt.utils import openLink
from aqt.qt import QPushButton, QHBoxLayout, QVBoxLayout

from .button_manager import mini_button
from .popup_config import REPORT_URL, PATREON_URL, RATE_THIS_URL

RIGHT_ALIGN_BUTTONS = True
LEFT_ALIGN_BUTTONS = False

def add_shige_buttons(main_layout:QVBoxLayout):
    # NOTE: Emoji may not display properly on Linux.

    button_layout = QHBoxLayout()
    if RIGHT_ALIGN_BUTTONS:
        button_layout.addStretch()

    rate_this_button = QPushButton('👍️RateThis')
    rate_this_button.clicked.connect(lambda: openLink(RATE_THIS_URL))
    mini_button(rate_this_button)

    patreon_button = QPushButton("💖Patreon")
    patreon_button.clicked.connect(lambda: openLink(PATREON_URL))
    mini_button(patreon_button)

    report_button = QPushButton("🚨Issues")
    report_button.clicked.connect(lambda: openLink(REPORT_URL))
    mini_button(report_button)

    button_layout.addWidget(rate_this_button)
    button_layout.addWidget(patreon_button)
    button_layout.addWidget(report_button)

    if LEFT_ALIGN_BUTTONS:
        button_layout.addStretch()

    main_layout.addLayout(button_layout)
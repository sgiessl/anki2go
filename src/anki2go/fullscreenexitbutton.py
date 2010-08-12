# Copyright (C) 2010  Sandro Giessl <sgiessl@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt4 import QtCore
from PyQt4.QtCore import QEvent
from PyQt4.QtGui import QToolButton
from PyQt4.QtGui import QIcon
from PyQt4.QtCore import QTimer

class FullScreenExitButton(QToolButton):
    def __init__(self, parent, bottomOffset):
        self.window = parent
        self.bottomOffset = bottomOffset
        QToolButton.__init__(self, parent)
        # set the fullsize icon from Maemo's theme
        self.setIcon(QIcon.fromTheme("general_fullsize"));

        # ensure that our size is fixed to our ideal size
        self.setFixedSize(self.sizeHint());

        # set the background to 0.5 alpha
        pal = self.palette();
        backgroundColor = pal.color(self.backgroundRole());
        backgroundColor.setAlpha(128);
        pal.setColor(self.backgroundRole(), backgroundColor);
        self.setPalette(pal);

        # ensure that we're painting our background
        self.setAutoFillBackground(True);

        # when we're clicked, tell the parent to exit fullscreen
        self.connect(self, QtCore.SIGNAL("clicked()"), parent.showNormal);

        # install an event filter to listen for the parent's events
        parent.installEventFilter(self);

    # def updatePosition(self):
    #     parent = self.parentWidget()
    #     if self.isVisible():
    #         self.move(parent.width() - self.width(),
    #                   parent.height() - self.height() - self.bottomOffset);

    def eventFilter(self, obj, ev):
        parent = self.window
        if (obj != parent):
            return QToolButton.eventFilter(self, obj, ev);

        parent = self.window
        isFullScreen = parent.windowState() & QtCore.Qt.WindowFullScreen

        if ev.type() == QEvent.WindowStateChange:
            self.setVisible(isFullScreen)
            # if isFullScreen:
            #     self.raise_();

        # if ev.type() == QEvent.WindowStateChange or ev.type == QEvent.Resize:
        #     # needs to be delayed casue for some reason parent's
        #     # dimensions aren't up to date yet
        #     QTimer.singleShot(30, self.updatePosition)

        return QToolButton.eventFilter(self, obj, ev)

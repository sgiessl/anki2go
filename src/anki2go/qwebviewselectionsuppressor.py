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

class QWebViewSelectionSuppressor(QtCore.QObject):
    def __init__(self, v):
        QtCore.QObject.__init__(self, v)
        self.enabled = False
        self.mousePressed = False
        self.view = v
        self.enable()

    def enable(self):
        if self.enabled:
            return
        self.view.installEventFilter(self)
        self.enabled = True

    def disable(self):
        if not enabled:
            return
        self.view.removeEventFilter(self)
        self.enabled = False

    def isEnabled(self):
        return self.enabled;

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonPress:
            if ev.button() == QtCore.Qt.LeftButton:
                self.mousePressed = True
        elif ev.type() == QEvent.MouseButtonRelease:
            if ev.button() == QtCore.Qt.LeftButton:
                self.mousePressed = False
        elif ev.type() == QEvent.MouseMove:
            if self.mousePressed:
                return True

        return False


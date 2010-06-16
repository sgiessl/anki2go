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
from PyQt4 import QtGui

class SettingsDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle("Settings")

        l = QtGui.QVBoxLayout()
        self.setLayout(l)

        self.maemoPlatform = False
        try:
            from PyQt4.QtMaemo5 import QMaemo5ValueButton
            from PyQt4.QtMaemo5 import QMaemo5ListPickSelector
            # from PyQt4.QtMaemo5 import QMaemo5TimePickSelector
            self.maemoPlatform = True
            self.picker = QMaemo5ListPickSelector(self)
            self.pickerModel = QtGui.QStandardItemModel(self)
            item = QtGui.QStandardItem("Landscape")
            item.setData(True)
            self.pickerModel.appendRow(item)
            item = QtGui.QStandardItem("Portrait")
            item.setData(False)
            self.pickerModel.appendRow(item)
            self.picker.setModel(self.pickerModel)
            self.picker.setCurrentIndex(0)
            self.orientationButton = QMaemo5ValueButton("Screen Rotation", self)
            self.orientationButton.setPickSelector(self.picker)

            l.addWidget(self.orientationButton)

        except ImportError, e:
            pass

        lbl = QtGui.QLabel('User:', self)
        l.addWidget(lbl)
        self.user = QtGui.QLineEdit(self)
        l.addWidget(self.user)

        lbl = QtGui.QLabel('Password:', self)
        l.addWidget(lbl)
        self.pw = QtGui.QLineEdit(self)
        self.pw.setEchoMode(QtGui.QLineEdit.Password)
        l.addWidget(self.pw)

        btns = QtGui.QDialogButtonBox(self)
        btns.addButton(QtGui.QDialogButtonBox.Ok)
        l.addWidget(btns)

        self.connect(btns, QtCore.SIGNAL("accepted()"), self.accept)
        self.connect(btns, QtCore.SIGNAL("rejected()"), self.reject)

    def setPortrait(self, port):
        if self.maemoPlatform:
            if port:
                self.picker.setCurrentIndex(1)
            else:
                self.picker.setCurrentIndex(0)
    def getPortrait(self):
        if self.maemoPlatform:
            return self.picker.currentIndex()==1
        else:
            return False

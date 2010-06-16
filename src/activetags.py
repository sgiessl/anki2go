# Copyright (C) 2010  Sandro Giessl <sgiessl@gmail.com>
#
# Taken with small modifications from ankiqt:
# Copyright: Damien Elmes <anki@ichi2.net>
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

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from anki.utils import parseTags, joinTags, canonifyTags

class ActiveTagsChooserUi:
    def __init__(self, dialog):
        dialog.setWindowTitle("Inactive Tags")
        self.dlg = dialog
        self.buttonBox = QDialogButtonBox(dialog)
        self.buttonBox.addButton(QDialogButtonBox.Ok)
        self.buttonBox.setOrientation(Qt.Vertical)
        self.list = QListWidget(dialog)
        self.list.setSelectionMode(QListWidget.MultiSelection)
        l = QHBoxLayout(self.dlg)
        self.dlg.setLayout(l)
        l.addWidget(self.list)
        l.addWidget(self.buttonBox)

        dialog.connect(self.buttonBox, SIGNAL("accepted()"), dialog.accept)
        dialog.connect(self.buttonBox, SIGNAL("rejected()"), dialog.reject)

class ActiveTagsChooser(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.deck = self.parent.deck
        self.dialog = ActiveTagsChooserUi(self)
        self.selectAll = QPushButton("Select All")
        self.connect(self.selectAll, SIGNAL("clicked()"), self.onSelectAll)
        self.dialog.buttonBox.addButton(self.selectAll,
                                        QDialogButtonBox.ActionRole)
        self.selectNone = QPushButton("Select None")
        self.connect(self.selectNone, SIGNAL("clicked()"), self.onSelectNone)
        self.dialog.buttonBox.addButton(self.selectNone,
                                        QDialogButtonBox.ActionRole)
        self.invert = QPushButton("Invert")
        self.connect(self.invert, SIGNAL("clicked()"), self.onInvert)
        self.dialog.buttonBox.addButton(self.invert,
                                        QDialogButtonBox.ActionRole)
        self.rebuildTagList()

    def onSelectAll(self):
        self.dialog.list.selectAll()

    def onSelectNone(self):
        self.dialog.list.clearSelection()

    def onInvert(self):
        sm = self.dialog.list.selectionModel()
        sel = sm.selection()
        self.dialog.list.selectAll()
        sm.select(sel, QItemSelectionModel.Deselect)

    def rebuildTagList(self):
        self.tags = self.deck.allTags()
        self.items = []
        self.suspended = {}
        alltags = []
        # get list of currently suspended
        for t in parseTags(self.deck.suspended):
            self.suspended[t] = 1
            if t not in self.tags:
                self.tags.append(t)
        # sort and remove special 'Suspended' tag
        self.tags.sort()
        # render models and templates
        for (type, sql, icon) in (
            ("models", "select tags from models", "contents.png"),
            ("cms", "select name from cardModels", "Anki_Card.png")):
            d = {}
            tagss = self.deck.s.column0(sql)
            for tags in tagss:
                for tag in parseTags(tags):
                    d[tag] = 1
            sortedtags = sorted(d.keys())
            alltags.extend(sortedtags)
            icon = QIcon(":/icons/" + icon)
            for t in sortedtags:
                item = QListWidgetItem(icon, t.replace("_", " "))
                self.dialog.list.addItem(item)
                self.items.append(item)
                idx = self.dialog.list.indexFromItem(item)
                if t in self.suspended:
                    mode = QItemSelectionModel.Select
                else:
                    mode = QItemSelectionModel.Deselect
                self.dialog.list.selectionModel().select(idx, mode)
        # remove from user tags
        for tag in alltags:
            try:
                self.tags.remove(tag)
            except:
                pass
        # user tags
        icon = QIcon(":/icons/Anki_Fact.png")
        for t in self.tags:
            item = QListWidgetItem(icon, t.replace("_", " "))
            self.dialog.list.addItem(item)
            self.items.append(item)
            idx = self.dialog.list.indexFromItem(item)
            if t in self.suspended:
                mode = QItemSelectionModel.Select
            else:
                mode = QItemSelectionModel.Deselect
            self.dialog.list.selectionModel().select(idx, mode)
        self.tags = alltags + self.tags

    def accept(self):
        self.hide()
        self.deck.startProgress()
        n = 0
        suspended = []
        for item in self.items:
            idx = self.dialog.list.indexFromItem(item)
            if self.dialog.list.selectionModel().isSelected(idx):
                suspended.append(self.tags[n])
            n += 1
        self.deck.suspended = canonifyTags(joinTags(suspended))
        self.deck.setModified()
        self.deck.updateAllPriorities(partial=True, dirty=False)
        self.deck.finishProgress()
        QDialog.accept(self)

def show(parent):
    at = ActiveTagsChooser(parent)
    at.exec_()

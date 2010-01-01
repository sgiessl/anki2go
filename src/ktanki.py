# Copyright (C) 2009  Ruslan Spivak
# http://ruslanspivak.com
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
import os
import sys
import time

from functools import partial
from ConfigParser import ConfigParser

from PyQt4 import QtGui
from PyQt4 import QtCore

from anki import DeckStorage
from anki.sync import SyncClient
from anki.sync import HttpSyncServerProxy

CONFIG_PATH = '~/.ktankirc'


class KTAnki(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Simple Reviewer - Anki')

        self._init_menu_bar()

        self._init_central_widget()

        self.deck_path = None
        self.deck = None
        self.current_card = None

        self.config = config = ConfigParser()
        config.read(os.path.expanduser(CONFIG_PATH))

    def open(self):
        self.deck_path = QtGui.QFileDialog.getOpenFileName(
            self, 'Open', '.', 'Anki deck files (*.anki)')
        # QString --> str
        self.deck_path = str(self.deck_path)

        try:
            self.deck = DeckStorage.Deck(self.deck_path, backup=False)
            self.deck.initUndo()
            self.deck.rebuildQueue()
        except Exception, e:
            QtGui.QMessageBox.critical(self, 'Open error', e.message)
        else:
            self.textedit.clear()
            self._reset_display()
            self.show_question()
            self.show_stats()

    def save(self):
        if self.deck is None:
            return

        if not self.deck.modifiedSinceSave():
            return

        reply = QtGui.QMessageBox.question(
            self, 'Ktanki - Unsaved changes',
            'Save unsaved changes?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.display_doc(
                '<center><br/>Saving %s...</center>' % self.deck_path)
            try:
                self.deck.save()
            except Exception, e:
                QtGui.QMessageBox.critical(self, 'Save error', e.message)
            else:
                self.save_button.setStyleSheet(self.save_button_style)
                self.show_question()

    def sync(self):
        config = self.config
        try:
            sync_username = config.get('ktanki', 'sync_username')
            sync_password = config.get('ktanki', 'sync_password')
        except Exception, e:
            QtGui.QMessageBox.critical(self, 'Sync error', e.message)
            return

        self.deck.save()
        self.deck.lastLoaded = time.time()

        proxy = HttpSyncServerProxy(sync_username, sync_password)
        try:
            proxy.connect('ankimini')
        except Exception, e:
            QtGui.QMessageBox.critical(
                self, 'Sync error',
                'Cant sync - check connection and username/password')
            return

        if not proxy.hasDeck(self.deck.syncName):
            QtGui.QMessageBox.critical(
                self, 'Sync error', 'Cant sync, no deck on server')
            return

        if abs(proxy.timestamp - time.time()) > 60:
            QtGui.QMessageBox.critical(
                self, 'Sync error',
                ('Your clock is off by more than 60 seconds. '
                 'Syncing will not work until you fix this.'))
            return

        client = SyncClient(self.deck)
        client.setServer(proxy)
        # need to do anything?
        proxy.deckName = self.deck.syncName
        if not client.prepareSync():
            QtGui.QMessageBox.information(self, 'Sync', 'Nothing to do')
            return

        # summary
        page = 'Fetching summary from server..<br>'
        self.display_doc(page)
        sums = client.summaries()

        # diff
        page += 'Determining differences..'
        self.display_doc(page)
        payload = client.genPayload(sums)

        # send payload
        pr = client.payloadChangeReport(payload)
        page += '<br>' + pr + '<br>'
        page += 'Sending payload...<br>'
        self.display_doc(page)
        res = client.server.applyPayload(payload)

        # apply reply
        page += 'Applying reply..<br>'
        self.display_doc(page)
        client.applyPayloadReply(res)

        # finished. save deck, preserving mod time
        page += 'Sync complete.'
        self.display_doc(page)
        self.deck.rebuildQueue()
        self.deck.lastLoaded = self.deck.modified
        self.deck.s.flush()
        self.deck.s.commit()

        # show question
        QtGui.QMessageBox.information(self, 'Sync', 'Sync completed.')
        self._reset_display()
        self.show_question()
        self.show_stats()

    def undo(self):
        if self.deck is not None:
            self.deck.undo()
            self.deck.refresh()
            self.deck.updateAllPriorities()
            self.deck.rebuildCounts()
            self.deck.rebuildQueue()
            self._reset_display()
            self.show_question()
            self.show_stats()

    def _init_menu_bar(self):
        open_action = QtGui.QAction('Open...', self)
        self.connect(open_action, QtCore.SIGNAL('triggered()'), self.open)

        save_action = QtGui.QAction('Save', self)
        self.connect(save_action, QtCore.SIGNAL('triggered()'), self.save)

        exit_action = QtGui.QAction('Exit', self)
        self.connect(exit_action, QtCore.SIGNAL('triggered()'), self.close)

        menubar = self.menuBar()
        file = menubar.addAction(open_action)
        file = menubar.addAction(save_action)
        file = menubar.addAction(exit_action)


    def _init_central_widget(self):
        main_widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout()
        main_widget.setLayout(main_layout)
        main_layout.setSpacing(0)

        # stats
        stats_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(stats_layout)
        self.stats_label = stats_label = QtGui.QLabel()
        stats_layout.addWidget(stats_label)
        self.stats2_label = stats2_label = QtGui.QLabel()
        stats_layout.addWidget(stats2_label)

        # top buttons
        self.options_widget = options_widget = QtGui.QWidget()
        options_layout = QtGui.QHBoxLayout()
        options_widget.setLayout(options_layout)
        main_layout.addWidget(options_widget)
        self.save_button = save_button = QtGui.QPushButton('Save')
        self.save_button_style = save_button.styleSheet()

        sync_button = QtGui.QPushButton('Sync')
        undo_button = QtGui.QPushButton('Undo Answer')
        options_layout.addWidget(save_button)
        options_layout.addWidget(sync_button)
        options_layout.addWidget(undo_button)

        # central read-only QTextEdit widget
        self.textedit = QtGui.QTextEdit()
        self.textedit.setReadOnly(True)
        main_layout.addWidget(self.textedit)

        # answer
        self.answer_widget = answer_widget = QtGui.QWidget()
        answer_layout = QtGui.QHBoxLayout()
        answer_layout.setSpacing(0)
        answer_widget.setLayout(answer_layout)
        main_layout.addWidget(answer_widget)
        answer_button = QtGui.QPushButton('Show Answer')
        answer_layout.addWidget(answer_button)

        # learn/review buttons
        self.learnmore_widget = learnmore_widget = QtGui.QWidget()
        learnmore_layout = QtGui.QHBoxLayout()
        learnmore_layout.setSpacing(0)
        learnmore_button = QtGui.QPushButton('Learn More')
        reviewearly_button = QtGui.QPushButton('Review Early')
        learnmore_layout.addWidget(learnmore_button)
        learnmore_layout.addWidget(reviewearly_button)
        learnmore_widget.setLayout(learnmore_layout)
        main_layout.addWidget(learnmore_widget)

        # repeat interval buttons
        self.repeat_widget = repeat_widget = QtGui.QWidget()
        repeat_layout = QtGui.QHBoxLayout()
        repeat_layout.setSpacing(0)
        repeat_widget.setLayout(repeat_layout)
        main_layout.addWidget(repeat_widget)
        self.repeat_buttons = []
        for index in range(4):
            if index == 0:
                button = QtGui.QPushButton('Soon')
            else:
                button = QtGui.QPushButton(str(index))
            self.connect(button, QtCore.SIGNAL('clicked()'),
                         partial(self.repeat_clicked, index+1))
            repeat_layout.addWidget(button)
            self.repeat_buttons.append(button)

        # signals/slots
        self.connect(answer_button, QtCore.SIGNAL('clicked()'),
                     partial(self.button_clicked, 'answer'))
        self.connect(learnmore_button, QtCore.SIGNAL('clicked()'),
                     partial(self.button_clicked, 'learn_more'))
        self.connect(reviewearly_button, QtCore.SIGNAL('clicked()'),
                     partial(self.button_clicked, 'review_early'))
        self.connect(save_button, QtCore.SIGNAL('clicked()'), self.save)
        self.connect(sync_button, QtCore.SIGNAL('clicked()'), self.sync)
        self.connect(undo_button, QtCore.SIGNAL('clicked()'), self.undo)

        # central widget
        self.setCentralWidget(main_widget)

        self._reset_display()

    def _reset_display(self):
        # show/hide widgets for initial display
        self.options_widget.hide()
        self. answer_widget.hide()
        self.learnmore_widget.hide()
        self.repeat_widget.hide()

    def button_clicked(self, cmd):
        if cmd == 'answer':
            self.answer_widget.hide()
            self.learnmore_widget.hide()
            self.repeat_widget.show()
            self.show_answer()

        elif cmd == 'learn_more':
            self.deck.newEarly = True
            self.deck.refresh()
            self.deck.updateAllPriorities()
            self.deck.rebuildCounts()
            self.deck.rebuildQueue()

            self.answer_widget.show()
            self.learnmore_widget.hide()
            self.repeat_widget.hide()
            self.show_question()
            self.show_stats()

        elif cmd == 'review_early':
            self.deck.reviewEarly = True
            self.deck.refresh()
            self.deck.updateAllPriorities()
            self.deck.rebuildCounts()
            self.deck.rebuildQueue()

            self.answer_widget.show()
            self.learnmore_widget.hide()
            self.repeat_widget.hide()
            self.show_question()
            self.show_stats()

    def repeat_clicked(self, ease):
        """@ease - integer"""
        if self.current_card is not None:
            self.deck.answerCard(self.current_card, ease)
        self.show_question()
        self.show_stats()

    def show_question(self):
        question_tmpl = '<center><div class="question">%s</div></center>'
        card = self.current_card = self.deck.getCard(orm=False)

        if card is not None:
            self.options_widget.show()
            self.answer_widget.show()
            self.learnmore_widget.hide()
            self.repeat_widget.hide()
            self.display_doc(question_tmpl % card.question)
        else:
            self.answer_widget.hide()
            self.repeat_widget.hide()
            self.learnmore_widget.show()
            self.display_doc(self.deck.deckFinishedMsg())

        if self.deck.modifiedSinceSave():
            self.save_button.setStyleSheet('background-color: red; ')
        else:
            self.save_button.setStyleSheet(self.save_button_style)

    def show_answer(self):
        if self.current_card is None:
            self.current_card = self.deck.getCard(orm=False)
        card = self.current_card
        card_qa = """
        <center>
        <div class="question">%s</div>
        <div class="answer"> %s </div>
        </center>
        """ % (card.question, card.answer)

        self.options_widget.show()
        self.answer_widget.hide()
        self.learnmore_widget.hide()
        self.repeat_widget.show()

        self.display_doc(card_qa)

        for index in range(2, 5):
            self.repeat_buttons[index-1].setText(
                self.deck.nextIntervalStr(card, index, True))

    def display_doc(self, html):
        doc = """
        <html>
          <head>
            <style>
              .question { font-size: 30px; color: #0000ff; }
              .answer { font-size: 30px; }
              body { margin: 0px; padding: 0px; }
            </style>
          </head>
          <body>
          %s
          </body>
        </html>
        """ % html
        self.textedit.setHtml(doc)
        self.textedit.repaint()

    def show_stats(self):
        s = self.deck.getStats(short=True)
        stats = (
            ("T: %(dYesTotal)d/%(dTotal)d "
             "(%(dYesTotal%)3.1f%%) "
             "A: <b>%(gMatureYes%)3.1f%%</b>. ETA: <b>%(timeLeft)s</b>") % s)
        f = "<font color=#990000>%(failed)d</font>"
        r = '<font color="green">%(rev)d</font>'
        n = "<font color=#0000ff>%(new)d</font>"
        if self.current_card is not None:
            if self.current_card.reps:
                if self.current_card.successive:
                    r = "<u>" + r + "</u>"
                else:
                    f = "<u>" + f + "</u>"
            else:
                n = "<u>" + n + "</u>"
        stats2 = ("<font size=+2>%s+%s+%s</font>" % (f, r, n)) % s
        self.stats_label.setText(stats)
        self.stats2_label.setText(stats2)


def main():
    app = QtGui.QApplication(sys.argv)

    ktanki = KTAnki()
    ktanki.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()





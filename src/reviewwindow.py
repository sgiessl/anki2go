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
import os
import sys
import time
import datetime

from qwebviewselectionsuppressor import QWebViewSelectionSuppressor
from fullscreenexitbutton import FullScreenExitButton

from functools import partial

from anki.utils import parseTags, joinTags

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtWebKit import QWebView
from PyQt4.QtCore import QUrl

# # default is 60 seconds
# REFRESH_TIME = 60 * 1000

class ReviewWindow(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.parent = parent

        self.maemoPlatform = False
        try:
            from PyQt4.QtMaemo5 import QMaemo5ValueButton
            self.maemoPlatform = True
        except ImportError, e:
            pass

        if self.maemoPlatform:
            self.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow);

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window);

        self.setWindowTitle('Review Deck')

        self.current_card = None

        self._init_menu_bar()

        self._init_central_widget()

    def undo(self):
        deck = self.parent.deck
        if deck is not None:
            deck.undo()
            deck.refresh()
            deck.updateAllPriorities()
            deck.rebuildCounts()
            deck.rebuildQueue()
            self._reset_display()
            self.show_question()

    def _init_menu_bar(self):
        zoom_in_action = QtGui.QAction('Zoom &In', self)
        self.connect(zoom_in_action, QtCore.SIGNAL('triggered()'),
                     self.zoomIn)

        zoom_out_action = QtGui.QAction('Zoom &Out', self)
        self.connect(zoom_out_action, QtCore.SIGNAL('triggered()'),
                     self.zoomOut)

        undo_action = QtGui.QAction('&Undo Last Answer', self)
        self.connect(undo_action, QtCore.SIGNAL('triggered()'),
                     self.undo)

        fullscreen_action = QtGui.QAction('&Fullscreen', self)
        self.connect(fullscreen_action, QtCore.SIGNAL('triggered()'),
                     self.toggleFullScreen)

        settings_action = QtGui.QAction('&Settings', self)
        self.connect(settings_action, QtCore.SIGNAL('triggered()'),
                     self.parent.show_settings)

        menubar = self.menuBar()
        menubar.addAction(zoom_in_action)
        menubar.addAction(zoom_out_action)
        menubar.addAction(undo_action)
        menubar.addAction(fullscreen_action)
        menubar.addAction(settings_action)

    def _init_central_widget(self):
        # self.setBackgroundRole(QtGui.QPalette.Base)

        main_widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout()
        main_widget.setLayout(main_layout)
        # main_layout.setSpacing(0)
        main_layout.setMargin(0)

        # stats
        stats_layout = QtGui.QHBoxLayout()
        main_layout.addLayout(stats_layout)
        self.stats_label = stats_label = QtGui.QLabel()
        stats_layout.addWidget(stats_label)
        stats_layout.addStretch()
        self.stats3_label = stats_label = QtGui.QLabel()
        stats_layout.addWidget(stats_label)
        stats_layout.addStretch()
        self.stats2_label = stats2_label = QtGui.QLabel()
        stats_layout.addWidget(stats2_label)

        # central read-only html rendering widget
        self.webview = QWebView()
        self.webview.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                                   QtGui.QSizePolicy.MinimumExpanding)
        self.viewSelectionSuppressor = QWebViewSelectionSuppressor(self.webview)
        main_layout.addWidget(self.webview)

        # answer
        self.answer_widget = answer_widget = QtGui.QWidget()
        answer_layout = QtGui.QHBoxLayout()
        answer_layout.setSpacing(0)
        answer_widget.setLayout(answer_layout)
        main_layout.addWidget(answer_widget)
        self.mark_button = QtGui.QPushButton('Mark')
        self.mark_button.setCheckable(True)
        answer_layout.addWidget(self.mark_button, 0)
        answer_button = QtGui.QPushButton('Show Answer')
        answer_layout.addWidget(answer_button, 1)

        offset = self.answer_widget.sizeHint().height()
        self.fullscreenexitbutton = FullScreenExitButton(self,offset)
        self.fullscreenexitbutton.setVisible(False)
        stats_layout.addWidget(self.fullscreenexitbutton)

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
                     self.slot_answer)
        self.connect(self.mark_button, QtCore.SIGNAL('toggled(bool)'),
                     self.slot_mark)
        self.connect(learnmore_button, QtCore.SIGNAL('clicked()'),
                     self.slot_learn_more)
        self.connect(reviewearly_button, QtCore.SIGNAL('clicked()'),
                     self.slot_review_early)

        # central widget
        self.setCentralWidget(main_widget)

        self._reset_display()

    def _reset_display(self):
        # show/hide widgets for initial display
        self.answer_widget.hide()
        self.learnmore_widget.hide()
        self.repeat_widget.hide()

    def toggleFullScreen(self):
        isFullScreen = self.windowState() & QtCore.Qt.WindowFullScreen
        if isFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

    def toggleBusyIndicator(state):
        self.setAttribute(QtCore.Qt.WA_Maemo5ShowProgressIndicator, state == QtCore.Qt.Checked)

    def zoomIn(self):
        self.setZoom(self.zoom + 25)

    def zoomOut(self):
        self.setZoom(self.zoom - 25)

    def setZoom(self, value):
        if value < 25:
            value = 25
        if value > 300:
            value = 300

        self.zoom = value
        self.webview.setZoomFactor(value/100.0)
        self.parent.config.set('anki2go', 'zoom', value)
        self.parent.write_config()

    def slot_answer(self):
        deck = self.parent.deck
        self.answer_widget.hide()
        self.learnmore_widget.hide()
        self.repeat_widget.show()
        self.show_answer()

    def slot_mark(self, new_mark):
        deck = self.parent.deck
        card = self.current_card
        marked = "marked" in card.tags.lower()
        if not marked and new_mark:
            card.tags = joinTags(parseTags(card.tags) + ["Marked"])
            card.toDB(deck.s)
        elif marked and not new_mark:
            t = parseTags(card.tags)
            t.remove("Marked")
            card.tags = joinTags(t)

    def slot_learn_more(self):
        deck = self.parent.deck
        deck.newEarly = True
        deck.refresh()
        deck.updateAllPriorities()
        deck.rebuildCounts()
        deck.rebuildQueue()

        self.answer_widget.show()
        self.learnmore_widget.hide()
        self.repeat_widget.hide()
        self.show_question()

    def slot_review_early():
        deck = self.parent.deck
        deck.reviewEarly = True
        deck.refresh()
        deck.updateAllPriorities()
        deck.rebuildCounts()
        deck.rebuildQueue()

        self.answer_widget.show()
        self.learnmore_widget.hide()
        self.repeat_widget.hide()
        self.show_question()

    def repeat_clicked(self, ease):
        """@ease - integer"""
        deck = self.parent.deck
        if self.current_card is not None:
            deck.answerCard(self.current_card, ease)
        self.show_question()

    def get_future_warning(self):
        deck = self.parent.deck
        if (self.current_card is None
            or self.current_card.due <= time.time()
            or self.current_card.due - time.time() <= deck.delay0
            ):
            return ''
        warning = (
            '<center><span style="color: red;">' +
            'This card was due in %s.' % fmtTimeSpan(
                self.current_card.due - time.time(), after=False) +
            '</span></center>'
            )
        return warning

    def show_question(self):
        self._reset_display()

        self.show_stats()

        deck = self.parent.deck
        card = self.current_card = deck.getCard(orm=False)
        if card is not None:
            question_tmpl = self.get_future_warning()
            question_tmpl += '<center><div class="question">%s</div></center>'
            if card and "marked" in card.tags.lower():
                self.mark_button.setChecked(True)
            else:
                self.mark_button.setChecked(False)
            self.answer_widget.show()
            self.display_doc(question_tmpl % card.question)
        else:
            deck.save()
            self.learnmore_widget.show()
            self.display_doc(deck.deckFinishedMsg())

    def show_answer(self):
        deck = self.parent.deck
        if self.current_card is None:
            self.current_card = deck.getCard(orm=False)
        card = self.current_card
        card_qa = """
        <center>
        <div class="question">%s</div>
        <div class="answer"> %s </div>
        </center>
        """ % (card.question, card.answer)

        self.answer_widget.hide()
        self.learnmore_widget.hide()
        self.repeat_widget.show()

        self.display_doc(card_qa)

        for index in range(2, 5):
            self.repeat_buttons[index-1].setText(
                deck.nextIntervalStr(card, index, True))

    def closeEvent(self, event):
        "Called before the review window is going to be closed"
        deck = self.parent.deck
        deck.resetAfterReviewEarly()
        deck.save()

        event.accept()

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

        deck = self.parent.deck
        if deck.mediaDir() != None:
            # os.chdir(deck.mediaDir())
            self.webview.setHtml(doc, QUrl("file://%s/" % deck.mediaDir()) )
        else:
            self.webview.setHtml(doc);

    def show_stats(self):
        deck = self.parent.deck
        s = deck.getStats(short=True)
        stats = (
            ("<b>%(dYesTotal)d/%(dTotal)d "
             "(%(dYesTotal%)3.1f%%)</b>") % s)
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

        stats2 = (("<b>%s+%s+%s</b>" % (f, r, n)) % s)
        stats3 = ''
        if s['dTotal'] > 0:
            stats3 = "<b>%s</b>" % s['timeLeft']
        self.stats_label.setText(stats)
        self.stats3_label.setText(stats3)
        self.stats2_label.setText("%s" % stats2)

    def start_refresh_timer(self):
        """Update statistic periodically."""
        # self.refresh_timer = QtCore.QTimer(self)
        # self.refresh_timer.start(REFRESH_TIME)
        # self.connect(self.refresh_timer, QtCore.SIGNAL('timeout()'),
        #              self.show_stats)
        pass


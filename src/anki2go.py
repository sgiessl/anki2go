# Copyright (C) 2010  Sandro Giessl <sgiessl@gmail.com>
# Copyright (C) 2009  Ruslan Spivak http://ruslanspivak.com
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
from settingsdialog import SettingsDialog
from activetags import ActiveTagsChooser
from reviewwindow import ReviewWindow

from functools import partial
from functools import wraps
from ConfigParser import ConfigParser

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtWebKit import QWebPage
from PyQt4.QtWebKit import QWebView
from PyQt4.QtCore import QUrl

from anki import DeckStorage
from anki.sync import SyncClient
from anki.sync import HttpSyncServerProxy
from anki.utils import fmtTimeSpan

CONFIG_PATH = '~/.anki2gorc'

class Anki2Go(QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.maemoPlatform = False
        try:
            from PyQt4.QtMaemo5 import QMaemo5ValueButton
            self.maemoPlatform = True
        except ImportError, e:
            pass

        self.setWindowTitle('Anki2Go')

        self._init_menu_bar()

        self._init_central_widget()

        self.deck_path = None
        self.deck = None
        self.current_card = None

        self.config = config = ConfigParser()

        config.read(os.path.expanduser(CONFIG_PATH))
        if not self.config.has_section('anki2go'):
            self.config.add_section('anki2go')

        if self.maemoPlatform:
            self.setAttribute(QtCore.Qt.WA_Maemo5StackedWindow);
        self.reviewWindow = ReviewWindow(self)

        try:
            orient = bool(self.config.get('anki2go', 'orientationPortrait'))
            self.setPortraitOrientation(orient)
        except Exception, e:
            print e.message
            self.setPortraitOrientation(False)
            pass

        try:
            filepath = self.config.get('anki2go', 'recent_deck_path')
            self.openPath(filepath)
        except:
            pass

        try:
            zoom = float(self.config.get('anki2go', 'zoom'))
            self.reviewWindow.setZoom(zoom)
        except:
            self.reviewWindow.setZoom(100)
            pass

    def setPortraitOrientation(self, portrait):
        self.portraitOrientation = portrait

        if not self.maemoPlatform:
            return

        self.setAttribute(QtCore.Qt.WA_Maemo5LandscapeOrientation, not portrait);
        self.setAttribute(QtCore.Qt.WA_Maemo5PortraitOrientation, portrait);
            # self.setAttribute(QtCore.Qt.WA_Maemo5AutoOrientation, True);

    def getPortraitOrientation(self):
        return self.portraitOrientation

    def open(self):
        path = QtGui.QFileDialog.getOpenFileName(
            self, 'Open', '.', 'Anki deck files (*.anki)')
        # QString --> str
        self.openPath(str(path))

    def openPath(self, path):
        try:
            self.deck = DeckStorage.Deck(path, backup=False)
            self.deck.initUndo()
            self.deck.rebuildQueue()
        except Exception, e:
            QtGui.QMessageBox.critical(self, 'Open error', e.message)
        else:
            self.webview.setHtml("<html><body></body></html>");
            self.show_study_options()
            self.deck_path = str(path)

        self.config.set('anki2go', 'recent_deck_path', self.deck_path)
        self.write_config()

    def save(self):
        if self.deck is None:
            return

        if not self.deck.modifiedSinceSave():
            return

        reply = QtGui.QMessageBox.question(
            self, 'Anki2Go - Unsaved changes',
            'Save unsaved changes?',
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.display_doc(
                '<center><br/>Saving %s...</center>' % self.deck_path)
            try:
                self.deck.save()
            except Exception, e:
                QtGui.QMessageBox.critical(self, 'Save error', e.message)

    def sync(self):
        try:
            sync_username = self.config.get('anki2go', 'sync_username')
            sync_password = self.config.get('anki2go', 'sync_password')
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
        QtGui.QMessageBox.information(self, 'Sync', 'Sync completed. %s' % pr)

        self.show_study_options()

    def _init_menu_bar(self):
        open_action = QtGui.QAction('&Open', self)
        self.connect(open_action, QtCore.SIGNAL('triggered()'), self.open)

        save_action = QtGui.QAction('&Save', self)
        self.connect(save_action, QtCore.SIGNAL('triggered()'), self.save)

        sync_action = QtGui.QAction('S&ync', self)
        self.connect(sync_action, QtCore.SIGNAL('triggered()'), self.sync)

        active_tags_action = QtGui.QAction('Set &Inactive Tags', self)
        self.connect(active_tags_action, QtCore.SIGNAL('triggered()'),
                     self.activeTagsDialog)

        settings_action = QtGui.QAction('Se&ttings', self)
        self.connect(settings_action, QtCore.SIGNAL('triggered()'),
                     self.show_settings)

        menubar = self.menuBar()
        menubar.addAction(open_action)
        menubar.addAction(save_action)
        menubar.addAction(sync_action)
        menubar.addAction(active_tags_action)
        menubar.addAction(settings_action)

    def _init_central_widget(self):
        main_widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout()
        main_widget.setLayout(main_layout)
        main_layout.setSpacing(0)

        # central read-only html rendering widget
        self.webview = QWebView()
        self.viewSelectionSuppressor = QWebViewSelectionSuppressor(self.webview)
        main_layout.addWidget(self.webview)

        # continue reviewing button
        self.contreview_widget = contreview_widget = QtGui.QWidget()
        contreview_layout = QtGui.QHBoxLayout()
        contreview_layout.setSpacing(0)
        contreview_widget.setLayout(contreview_layout)
        main_layout.addWidget(contreview_widget)
        sync_button = QtGui.QPushButton('Sync')
        contreview_button = QtGui.QPushButton('Continue Reviewing')
        contreview_layout.addWidget(sync_button)
        contreview_layout.addWidget(contreview_button)
        contreview_widget.hide()

        # signals/slots
        self.connect(contreview_button, QtCore.SIGNAL('clicked()'),
                     self.showReviewWindow)

        self.connect(sync_button, QtCore.SIGNAL('clicked()'), self.sync)

        # central widget
        self.setCentralWidget(main_widget)

    def showReviewWindow(self):
        self.reviewWindow.show_question()
        self.reviewWindow.setVisible(True)

    def show_study_options(self):
        self.deck.resetAfterReviewEarly()
        self.deck.save()

        self.contreview_widget.show()
        self.show_study_stats()

    def show_settings(self):
        dlg = SettingsDialog(self)
        try:
            sync_username = self.config.get('anki2go', 'sync_username')
            sync_password = self.config.get('anki2go', 'sync_password')
            dlg.user.setText(sync_username)
            dlg.pw.setText(sync_password)
        except:
            pass

        dlg.setPortrait( self.getPortraitOrientation() )
        if dlg.exec_() == QtGui.QDialog.Accepted:
            self.setPortraitOrientation(dlg.getPortrait())
            self.config.set('anki2go', 'sync_username', dlg.user.text())
            self.config.set('anki2go', 'sync_password', dlg.pw.text())
            self.config.set('anki2go', 'orientationPortrait', dlg.getPortrait())
            self.write_config()

    def activeTagsDialog(self):
        dlg = ActiveTagsChooser(self)
        if dlg.exec_() == QtGui.QDialog.Accepted:
            self.show_study_options()

    def write_config(self):
        try:
            configfile = open(os.path.expanduser(CONFIG_PATH), 'wb')
            self.config.write(configfile)
            configfile.close()
        except Exception, e:
            print e.message
            pass

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

        if self.deck.mediaDir() != None:
            # os.chdir(self.deck.mediaDir())
            self.webview.setHtml(doc, QUrl("file://%s/" % self.deck.mediaDir()) )
        else:
            self.webview.setHtml(doc);

    def show_study_stats(self):
        """Based on method from ankiqt."""
        was_reached = self.deck.sessionLimitReached()
        session_color = '<font color=#0000ff>%s</font>'
        card_color = '<font color=#0000ff>%s</font>'
        if not was_reached:
            top = "<h1>Study Options</h1>"
        else:
            top = "<h1>Well done!</h1>"
        # top label
        h = {}
        s = self.deck.getStats()
        h['ret'] = card_color % (s['rev'] + s['failed'])
        h['new'] = card_color % s['new']
        h['newof'] = str(self.deck.newCountAll())
        dtoday = s['dTotal']
        yesterday = self.deck._dailyStats.day - datetime.timedelta(1)
        res = self.deck.s.first("""
        select reps, reviewTime from stats where type = 1 and
        day = :d""", d=yesterday)
        if res:
            dyest, tyest = res
        else:
            dyest = tyest = 0
        h['repsToday'] = session_color % dtoday
        h['repsTodayChg'] = str(dyest)
        limit = self.deck.sessionTimeLimit
        start = self.deck.sessionStartTime or time.time() - limit
        start2 = self.deck.lastSessionStart or start - limit
        last10 = self.deck.s.scalar(
            "select count(*) from reviewHistory where time >= :t",
            t=start)
        last20 = self.deck.s.scalar(
            "select count(*) from reviewHistory where "
            "time >= :t and time < :t2",
            t=start2, t2=start)
        h['repsInSes'] = session_color % last10
        h['repsInSesChg'] = str(last20)
        ttoday = s['dReviewTime']
        h['timeToday'] = session_color % (
            fmtTimeSpan(ttoday, short=True, point=1))
        h['timeTodayChg'] = str(fmtTimeSpan(tyest, short=True, point=1))
        h['cs_header'] = "Cards/session:"
        h['cd_header'] = "Cards/day:"
        h['td_header'] = "Time/day:"
        h['rd_header'] = "Reviews due:"
        h['ntod_header'] = "New today:"
        h['ntot_header'] = "New total:"

        stats1 = ("""\
        <table>
        <tr><td width=80>%(cs_header)s</td>
        <td width=50><b>%(repsInSesChg)s</b></td>
        <td><b>%(repsInSes)s</b></td></tr>
        <tr><td>%(cd_header)s</td><td><b>%(repsTodayChg)s</b></td>
        <td><b>%(repsToday)s</b></td></tr>
        <tr><td>%(td_header)s</td><td><b>%(timeTodayChg)s</b></td>
        <td><b>%(timeToday)s</b></td></tr>
        </table>""") % h

        stats2 = ("""\
        <table>
        <tr><td width="140">%(rd_header)s</td>
        <td align="right"><b>%(ret)s</b></td></tr>
        <tr><td>%(ntod_header)s</td><td align="right"><b>%(new)s</b></td></tr>
        <tr><td>%(ntot_header)s</td><td align="right">%(newof)s</td></tr>
        </table>""") % h
        if not dyest and not dtoday:
            stats1 = ""
        else:
            stats1 = (
                "<td>%s</td><td>&nbsp;&nbsp;&nbsp;&nbsp;</td>" % stats1)
        self.display_doc(top + """\
        <p><table><tr>
        %s
        <td>%s</td></tr></table>""" % (stats1, stats2))

    def exit_app(self):
        self.write_config()
        if self.deck is not None and self.deck.modifiedSinceSave():
            reply = QtGui.QMessageBox.question(
                self, 'Anki2Go - Unsaved changes',
                'Save unsaved changes?',
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                try:
                    self.deck.save()
                except Exception, e:
                    QtGui.QMessageBox.critical(self, 'Save error', e.message)
                    return
        self.close()


def main():
    app = QtGui.QApplication(sys.argv)

    anki2go = Anki2Go()
    anki2go.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()





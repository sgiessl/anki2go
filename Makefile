#
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

BINFILE=bin/anki2go

CHANGELOG=CHANGES
CHANGELOG_TMP=.CHANGES.tmp
CHANGELOG_EDT=.CHANGES.edit
CHANGELOG_BKP=.CHANGES.backup
EMAIL ?= $$USER@`hostname -f`

DESTDIR ?= /
PREFIX ?= /usr

# default editor of user has not set "EDITOR" env variable
EDITOR ?= nano

all: help

help:
	@echo 'make test            run anki2go in local directory'
	@echo 'make mtest           run anki2go (for maemo scratchbox)'
	@echo 'make release         create source tarball in "dist/"'
	@echo 'make install         install anki2go into "$(PREFIX)"'
	@echo 'make uninstall       uninstall anki2go from "$(PREFIX)"'
	@echo 'make clean           remove generated+temp+*.py{c,o} files'
	@echo 'make distclean       do a "make clean" + remove "dist/"'
	@echo ''
	@echo '(1) Please set environment variable "EMAIL" to your e-mail address'

test:
	@# set xterm title to know what this window does ;)
	@echo -ne '\033]0;anki2go console (make test)\007'
	$(BINFILE) --verbose

mtest:
	@# in maemo scratchbox, we need this for osso/hildon
	run-standalone.sh python2.5 $(BINFILE) --maemo --verbose

deb:
	debuild

release: distclean
	python setup.py sdist

install:
	python setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

minstall:
	python2.5 setup.py install --root=$(DESTDIR) --prefix=$(PREFIX)

uninstall:
	rm -rf $(PREFIX)/share/anki2go $(PREFIX)/share/applications/anki2go.desktop $(PREFIX)/bin/anki2go $(PREFIX)/lib/python?.?/site-packages/anki2go/ $(PREFIX)/share/locale/anki2go.*


clean:
	python setup.py clean
	rm -f src/anki2go/*.pyc
	rm -rf build

debclean:
	fakeroot debian/rules clean

distclean: clean
	rm -rf dist

.PHONY: all test release install clean distclean help


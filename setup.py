#!/usr/bin/env python

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

import sys, os
import glob
import re
from distutils.core import setup

sys.path.insert(0, 'src')
import anki2go

# files to install
inst_desktop = [ 'data/anki2go.desktop' ]
inst_icon_64 = [ 'data/64x64/anki2go.png' ]

# data files
data_files = [
    # desktop file and icon are not optified  
    ('share/applications/hildon', inst_desktop),
    ('share/icons/hicolor/64x64/hildon', inst_icon_64),
]

# packages are always installed to the python path
packages = [
    # list classes to install them
    'anki2go',
]

author, email = re.match(r'^(.*) <(.*)>$', anki2go.__author__).groups()

setup(
  name             = 'anki2go',
  version          = anki2go.__version__,
  package_dir      = { '':'src' },
  packages         = packages,
  description      = 'Anki2Go is a lightweight client for reviewing anki decks',
  long_description = 'Anki2Go is a lightweight client for reviewing anki decks. For the moment, it is intended to run on the Maemo 5 platform with PyQt4 bindings and targets the Nokia N900 device.',
  author           = author,
  author_email     = email,
  url              = anki2go.__url__,
  scripts          = glob.glob('bin/*'),
  data_files       = data_files
)



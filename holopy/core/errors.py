# Copyright 2011-2016, Vinothan N. Manoharan, Thomas G. Dimiduk,
# Rebecca W. Perry, Jerome Fung, Ryan McGorty, Anna Wang, Solomon Barkley
#
# This file is part of HoloPy.
#
# HoloPy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HoloPy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HoloPy.  If not, see <http://www.gnu.org/licenses/>.

"""
Error classes used in holopy

.. moduleauthor :: Thomas G. Dimiduk <tdimiduk@physics.harvard.edu>
"""



class LoadError(Exception):
    def __init__(self, filename, message):
        self.filename = filename
        super(LoadError, self).__init__("Error loading file " + self.filename + ": " + self.message)

class BadImage(Exception):
    pass

class NoMetadata(Exception):
    def __str__(self):
        return "File without metadata detected. To load raw images, use hp.load_image()"

class CoordSysError(Exception):
    def __str__(self):
        return "Could not interpret your points. Use either Cartesian or spherical coordinates"

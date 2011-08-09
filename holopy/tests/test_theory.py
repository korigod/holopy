# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca
# W. Perry, Jerome Fung, and Ryan McGorty
#
# This file is part of Holopy.
#
# Holopy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Holopy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Holopy.  If not, see <http://www.gnu.org/licenses/>.
'''
Test construction and manipulation of scattering theory objects.

.. moduleauthor:: Vinothan N. Manoharan <vnm@seas.harvard.edu>
'''

import numpy as np
import holopy
import nose
from nose.tools import raises, assert_raises
from numpy.testing import (assert_, assert_equal, assert_almost_equal,
                           assert_array_almost_equal, assert_allclose)
from nose.tools import with_setup
import os
import string
from nose.plugins.attrib import attr

from holopy.model.scatterer import Sphere, CoatedSphere
from holopy.model.scatterer import Composite, SphereCluster

from holopy.model.theory import Mie
from holopy.model.calculate import calc_field, calc_holo, calc_intensity
from holopy import Optics
from holopy.model.errors import TheoryNotCompatibleError
from holopy.optics import WavelengthNotSpecified, PixelScaleNotSpecified

# nose setup/teardown methods
def setup_optics():
    # set up optics class for use in several test functions
    global optics
    wavelen = 658e-9
    polarization = [0., 1.0]
    divergence = 0
    pixel_scale = [.1151e-6, .1151e-6]
    index = 1.33
    
    optics = holopy.optics.Optics(wavelen=wavelen, index=index,
                                  pixel_scale=pixel_scale,
                                  polarization=polarization,
                                  divergence=divergence)
    
def teardown_optics():
    global optics
    del optics

@attr('fast')
@with_setup(setup=setup_optics, teardown=teardown_optics)
def test_Mie_construction():
    theory = Mie()
    assert_(theory.imshape == (256,256))
    theory = Mie(imshape=(100,100))
    assert_(theory.imshape == (100,100))

    # test with single value instead of tuple
    theory = Mie(imshape=128)
    assert_(theory.imshape == (128,128))

    # construct with optics
    theory = Mie(imshape=256, optics=optics)
    assert_(theory.optics.index == 1.33)

@attr('fast')
@with_setup(setup=setup_optics, teardown=teardown_optics)
def test_Mie_single():
    # try it with a single sphere first
    sc = Sphere(n=1.59, r=5e-7, x=1e-6, y=-1e-6, z=10e-6)
    theory = Mie(imshape=128, optics=optics)

    fields = theory.calc_field(sc)
    assert_allclose([f.sum() for f in fields], [(-0.083472463089860685+0.012770539644076111j),
                                                (-3.9082981023926409-22.567322348753319j),
                                                (-0.56230133684984218+2.768094495730304j)])
    assert_allclose([i.std() for i in fields], [0.0024371296061972384,
                                                0.044179364188274006,
                                                0.012691656014223607])
    
    theory.calc_intensity(sc)
    
    holo = theory.calc_holo(sc)
    assert_almost_equal(holo.sum(), 16370.390727161264)
    assert_almost_equal(holo.std(), 0.061010648908953205)
    
    # this shouldn't work because the theory doesn't know the pixel
    # scale 
    theory = Mie(imshape=128)
    assert_raises(PixelScaleNotSpecified, lambda:
                      theory.calc_field(sc))
    assert_raises(PixelScaleNotSpecified, lambda:
                      theory.calc_intensity(sc)) 
    assert_raises(PixelScaleNotSpecified, lambda:
                      theory.calc_holo(sc)) 

@attr('fast')
@with_setup(setup=setup_optics, teardown=teardown_optics)
def test_Mie_multiple():
    s1 = Sphere(n = 1.59, r = 5e-7, x = 1e-6, y = -1e-6, z = 10e-6)
    s2 = Sphere(n = 1.59, r = 1e-6, center=[8e-6,5e-6,5e-6])
    s3 = Sphere(n = 1.59+0.0001j, r = 5e-7, center=[5e-6,10e-6,3e-6])
    sc = SphereCluster(spheres=[s1, s2, s3])
    theory = Mie(imshape=128, optics=optics)

    fields = theory.calc_field(sc)
    assert_allclose([f.sum() for f in fields], [(0.0071378971541543289+0.082689606560838652j),
                                                (-490.32038052262499-3.1134313018817421j),
                                                (2.336770696224467+1.2237755614295063j)])
    assert_allclose([i.std() for i in fields], [0.01040974038137019,
                                                0.23932970855985464,
                                                0.047290610049841725])
    
    theory.calc_intensity(sc)

    holo = theory.calc_holo(sc)
    assert_almost_equal(holo.sum(), 16358.263330873539)
    assert_almost_equal(holo.std(), 0.21107984880858663)

    # should throw exception when fed a coated sphere
    assert_raises(TheoryNotCompatibleError, lambda: 
                  theory.calc_field(CoatedSphere()))
    assert_raises(TheoryNotCompatibleError, lambda: 
                  theory.calc_intensity(CoatedSphere()))
    assert_raises(TheoryNotCompatibleError, lambda: 
                  theory.calc_holo(CoatedSphere()))
    # and when the list of scatterers includes a coated sphere
    sc.add(CoatedSphere())
    assert_raises(TheoryNotCompatibleError, lambda: 
                  theory.calc_field(sc))
    assert_raises(TheoryNotCompatibleError, lambda: 
                  theory.calc_intensity(sc))
    assert_raises(TheoryNotCompatibleError, lambda: 
                  theory.calc_holo(sc))


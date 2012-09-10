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
Test fortran-based Mie calculations and python interface.  

.. moduleauthor:: Vinothan N. Manoharan <vnm@seas.harvard.edu>
.. moduleauthor:: Thomas G. Dimiduk <tdimiduk@physics.harvard.edu>
'''

import os
from nose.tools import with_setup, assert_raises
import yaml

import numpy as np
from numpy.testing import assert_equal
from numpy.testing import (assert_array_almost_equal, assert_almost_equal,
                           assert_raises)
from nose.plugins.attrib import attr

from ..scatterer import Sphere, Spheres, Ellipsoid
from ..theory import Mie

from ..theory.mie import UnrealizableScatterer
from ..errors import TheoryNotCompatibleError
from ...core import ImageSchema, Optics, Angles, GenericSchema
from .common import xoptics, yoptics, optics, verify
from ...core.tests.common import assert_allclose

# nose setup/teardown methods
def setup_model():
    global xschema, yschema, scaling_alpha, radius, n
    global n_particle_real, n_particle_imag, x, y, z

    scaling_alpha = .6
    radius = .85e-6
    n = 1.59+1e-4j
    n_particle_real = 1.59
    n_particle_imag = 1e-4
    x = .576e-05
    y = .576e-05
    z = 15e-6

    imshape = 128
    
    # set up optics class for use in several test functions
    xschema = ImageSchema(imshape, optics=xoptics)
    yschema = ImageSchema(imshape, optics=yoptics)

def teardown_model():
    global xschema, yschema, scaling_alpha, radius, n
    global n_particle_real, n_particle_imag, x, y, z
    del xschema, yschema, scaling_alpha, radius, n
    del n_particle_real, n_particle_imag, x, y, z


@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_single_sphere():
    # single sphere hologram (only tests that functions return)
    sphere = Sphere(n=n, r=radius, center=(x, y, z))

    holo = Mie.calc_holo(sphere, xschema, scaling=scaling_alpha)
    field = Mie.calc_field(sphere, xschema)

    intensity = Mie.calc_intensity(sphere, xschema)
    
    verify(holo, 'single_holo')
    verify(field, 'single_field')

    # now test some invalid scatterers and confirm that it rejects calculating
    # for them

    # large radius (calculation not attempted because it would take forever
    assert_raises(UnrealizableScatterer, Mie.calc_holo, Sphere(r=1), xschema)


@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_Mie_multiple():
    s1 = Sphere(n = 1.59, r = 5e-7, center = (1e-6, -1e-6, 10e-6))
    s2 = Sphere(n = 1.59, r = 1e-6, center=[8e-6,5e-6,5e-6])
    s3 = Sphere(n = 1.59+0.0001j, r = 5e-7, center=[5e-6,10e-6,3e-6])
    sc = Spheres(scatterers=[s1, s2, s3])

    schema = ImageSchema(128, optics = optics)
    fields = Mie.calc_field(sc, schema)

    verify(fields, 'mie_multiple_fields')
    Mie.calc_intensity(sc, schema)

    holo = Mie.calc_holo(sc, schema)
    verify(holo, 'mie_multiple_holo')

    # should throw exception when fed a ellipsoid
    el = Ellipsoid(n = 1.59, r = (1e-6, 2e-6, 3e-6), center=[8e-6,5e-6,5e-6])
    with assert_raises(TheoryNotCompatibleError) as cm:
        Mie.calc_field(el, schema)
    assert_equal(str(cm.exception), "The implementation of the Mie scattering "
                 "theory doesn't know how to handle scatterers of type "
                 "Ellipsoid")
    
    assert_raises(TheoryNotCompatibleError, Mie.calc_field, el, schema)
    assert_raises(TheoryNotCompatibleError, Mie.calc_intensity,
                  el, schema)
    assert_raises(TheoryNotCompatibleError, Mie.calc_holo, el, schema)
    # and when the list of scatterers includes a coated sphere
    sc.add(el)
    assert_raises(TheoryNotCompatibleError, Mie.calc_field, sc, schema)
    assert_raises(TheoryNotCompatibleError, Mie.calc_intensity, sc, schema)
    assert_raises(TheoryNotCompatibleError, Mie.calc_holo, sc, schema)
    
@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_mie_polarization():
    # test holograms for orthogonal polarizations; make sure they're
    # not the same, nor too different from one another.
    sphere = Sphere(n=n, r=radius, center=(x, y, z))

    xholo = Mie.calc_holo(sphere, xschema, scaling=scaling_alpha)
    yholo = Mie.calc_holo(sphere, yschema, scaling=scaling_alpha)

    # the two arrays should not be equal
    try:
        assert_array_almost_equal(xholo, yholo)
    except AssertionError:
        pass
    else:
        raise AssertionError("Holograms computed for both x- and y-polarized "
                             "light are too similar.")

    # but their max and min values should be close
    assert_almost_equal(xholo.max(), yholo.max())
    assert_almost_equal(xholo.min(), yholo.min())
    return xholo, yholo

@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_linearity():
    # look at superposition of scattering from two point particles;
    # make sure that this is sum of holograms from individual point
    # particles (scattered intensity should be negligible for this
    # case)

    x2 = x*2
    y2 = y*2
    z2 = z*2
    scaling_alpha = 1.0
    r = 1e-2*xoptics.wavelen    # something much smaller than wavelength

    sphere1 = Sphere(n=n, r=r, center = (x, y, z))
    sphere2 = Sphere(n=n, r=r, center = (x2, y2, z2))

    sc = Spheres(scatterers = [sphere1, sphere2])
    
    holo_1 = Mie.calc_holo(sphere1, xschema, scaling=scaling_alpha)
    holo_2 = Mie.calc_holo(sphere2, xschema, scaling=scaling_alpha)
    holo_super = Mie.calc_holo(sc, xschema, scaling=scaling_alpha)

    # make sure we're not just looking at uniform arrays (could
    # happen if the size is set too small)
    try:
        assert_array_almost_equal(holo_1, holo_2, decimal=12)
    except AssertionError:
        pass    # no way to do "assert array not equal" in numpy.testing
    else:
        raise AssertionError("Hologram computed for point particle" +
                             " looks suspiciously close to having" +
                             " no fringes")

    # Test linearity by subtracting off individual holograms.
    # This should recover the other hologram
    assert_array_almost_equal(holo_super - holo_1 + 1, holo_2)
    assert_array_almost_equal(holo_super - holo_2 + 1, holo_1)

    # uncomment to debug
    #return holo_1, holo_2, holo_super

@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_nonlinearity():
    # look at superposition of scattering from two large particles;
    # make sure that this is *not equal* to sum of holograms from
    # individual scatterers (scattered intensity should be
    # non-negligible for this case)

    x2 = x*2
    y2 = y*2
    z2 = z*2
    scaling_alpha = 1.0
    r = xoptics.wavelen    # order of wavelength

    sphere1 = Sphere(n=n, r=r, center = (x, y, z))
    sphere2 = Sphere(n=n, r=r, center = (x2, y2, z2))

    sc = Spheres(scatterers = [sphere1, sphere2])
    
    holo_1 = Mie.calc_holo(sphere1, xschema, scaling=scaling_alpha)
    holo_2 = Mie.calc_holo(sphere2, xschema, scaling=scaling_alpha)
    holo_super = Mie.calc_holo(sc, xschema, scaling=scaling_alpha)

    # test nonlinearity by subtracting off individual holograms
    try:
        assert_array_almost_equal(holo_super - holo_1 + 1, holo_2)
    except AssertionError:
        pass    # no way to do "assert array not equal" in numpy.testing
    else:
        raise AssertionError("Holograms computed for " 
                             "wavelength-scale scatterers should " 
                             "not superpose linearly")

    # uncomment to debug
    #return holo_1, holo_2, holo_super
@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_selection():
    sphere = Sphere(n=n, r=radius, center=(x, y, z))
    holo = Mie.calc_holo(sphere, xschema, scaling=scaling_alpha)

    
    subset_schema = ImageSchema(xschema.shape, optics = xoptics, use_random_fraction = .1)
    
    subset_holo = Mie.calc_holo(sphere, subset_schema, scaling=scaling_alpha)

    assert_allclose(subset_holo[subset_schema.selection], holo[subset_schema.selection])

@attr('fast')
@with_setup(setup = setup_model, teardown = teardown_model)
def test_radiometric():
    sphere = Sphere(n = n, r = radius, center = (x, y, z))
    cross_sects = Mie.calc_cross_sections(sphere, xoptics)
    # turn cross sections into efficiencies
    cross_sects[0:3] = cross_sects[0:3] / (np.pi * radius**2)

    # create a dict from the results
    result = {}
    result_keys = ['qscat', 'qabs', 'qext', 'costheta']
    for key, val in zip(result_keys, cross_sects):
        result[key] = val

    location = os.path.split(os.path.abspath(__file__))[0]
    gold_name = os.path.join(location, 'gold', 
                             'gold_mie_radiometric')
    gold = yaml.load(file(gold_name + '.yaml'))
    for key, val in gold.iteritems():
        assert_almost_equal(gold[key], val, decimal = 5)

@attr('fast')
@with_setup(setup = setup_model, teardown = teardown_model)
def test_farfield():
    schema = GenericSchema(positions = Angles(np.linspace(0, np.pi/2)), optics =
                                           Optics(wavelen=.66, index = 1.33))
    sphere = Sphere(r = .5, n = 1.59)

    matr = Mie.calc_scat_matrix(sphere, schema)

    
    

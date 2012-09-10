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
Test T-matrix sphere cluster calculations and python interface.  

.. moduleauthor:: Vinothan N. Manoharan <vnm@seas.harvard.edu>
'''
from __future__ import division

import sys
import os
import numpy as np

import warnings
from nose.tools import assert_raises, with_setup
from numpy.testing import (assert_equal, assert_array_almost_equal,
                           assert_almost_equal)

from nose.plugins.attrib import attr

from ...core import Optics, ImageSchema
from ..theory import Multisphere
from ..theory.multisphere import MultisphereExpansionNaN, ConvergenceFailureMultisphere
from ..scatterer import Sphere, Spheres, CoatedSphere
from ..errors import UnrealizableScatterer, TheoryNotCompatibleError
from .common import assert_allclose, verify

def setup_model():
    global xoptics, yoptics, scaling_alpha, radius, n_particle_imag
    global n_particle_real, x, y, z, imshape, wavelen
    
    # define optical train
    wavelen = 658e-9
    ypolarization = [0., 1.0] # y-polarized
    xpolarization = [1.0, 0.] # x-polarized
    divergence = 0
    pixel_scale = [.1151e-6, .1151e-6]
    index = 1.33

    yoptics = Optics(wavelen=wavelen, index=index,
                     pixel_scale=pixel_scale,
                     polarization=ypolarization,
                     divergence=divergence)

    xoptics = Optics(wavelen=wavelen, index=index,
                     pixel_scale=pixel_scale,
                     polarization=xpolarization,
                     divergence=divergence)

    scaling_alpha = .6
    radius = .85e-6
    n_particle_real = 1.59
    n_particle_imag = 1e-4
    x = .576e-05
    y = .576e-05
    z = 15e-6

    imshape = 128
    

def teardown_model():
    global xoptics, yoptics, scaling_alpha, radius, n_particle_imag
    global n_particle_real, x, y, z, imshape, wavelen

    del xoptics, yoptics, scaling_alpha, radius, n_particle_imag
    del n_particle_real, x, y, z, imshape, wavelen
    
@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_construction():
    # test constructor to make sure it works properly and calls base
    # class constructor properly
    theory = Multisphere(niter=100, eps=1e-6, meth=0, qeps1=1e-5, qeps2=1e-8)

    assert_equal(theory.niter, 100)
    assert_equal(theory.eps, 1e-6)
    assert_equal(theory.meth, 0)
    assert_equal(theory.qeps1, 1e-5)
    assert_equal(theory.qeps2, 1e-8)


@with_setup(setup=setup_model, teardown=teardown_model)
def test_polarization():
    # test holograms for orthogonal polarizations; make sure they're
    # not the same, nor too different from one another.

    sphere = Sphere(n=n_particle_real + n_particle_imag*1j, r=radius, 
                    center =(x, y, z))
    sc = Spheres([sphere])
    xschema = ImageSchema(shape = imshape, optics=xoptics)
    yschema = ImageSchema(shape = imshape, optics=yoptics)

    xholo = Multisphere.calc_holo(sc, xschema, scaling=scaling_alpha)
    yholo = Multisphere.calc_holo(sc, yschema, scaling=scaling_alpha)

    # the two arrays should not be equal
    try:
        assert_array_almost_equal(xholo, yholo)
    except AssertionError:
        pass
    else:
        raise AssertionError("Holograms computed for both x- and y-polarized light are too similar.")

    # but their max and min values should be close
    assert_almost_equal(xholo.max(), yholo.max())
    assert_almost_equal(xholo.min(), yholo.min())
    return xholo, yholo
    

@with_setup(setup=setup_model, teardown=teardown_model)
def test_2_sph():
    sc = Spheres(scatterers=[Sphere(center=[7.1e-6, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07),
                                Sphere(center=[6e-6, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07)])


    schema = ImageSchema(imshape, optics = xoptics)

    holo = Multisphere.calc_holo(sc, schema, scaling=.6)

    assert_almost_equal(holo.max(), 1.4140292298443309)
    assert_almost_equal(holo.mean(), 0.9955420925817654)
    assert_almost_equal(holo.std(), 0.09558537595025796)

@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_invalid():
    sc = Spheres(scatterers=[Sphere(center=[7.1, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07),
                                Sphere(center=[6e-6, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07)])

    schema = ImageSchema(imshape, optics = xoptics)

    assert_raises(UnrealizableScatterer, Multisphere.calc_holo, sc, schema)
    
    sc = Spheres(scatterers=[Sphere(center=[7.1, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-01),
                                Sphere(center=[6e-6, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07)])
    
    assert_raises(UnrealizableScatterer, Multisphere.calc_holo, sc, schema)

    sc.scatterers[0].r = -1

    assert_raises(UnrealizableScatterer, Multisphere.calc_holo, sc, schema)

    cs = CoatedSphere()

    assert_raises(TheoryNotCompatibleError, Multisphere.calc_holo, cs, schema)

@with_setup(setup=setup_model, teardown=teardown_model)
def test_overlap():
    # should raise a warning
    with warnings.catch_warnings(True) as w:
        warnings.simplefilter("always")
        sc = Spheres(scatterers=[Sphere(center=[3e-6, 3e-6, 10e-6], 
                                           n=1.59, r=.5e-6), 
                                    Sphere(center=[3.4e-6, 3e-6, 10e-6], 
                                           n=1.59, r=.5e-6)])
        assert len(w) > 0

    schema = ImageSchema(imshape, optics = xoptics)

    # should fail to converge
    assert_raises(MultisphereExpansionNaN, Multisphere.calc_holo, sc, schema)

    # but it should succeed with a small overlap, after raising a warning
    with warnings.catch_warnings(True) as w:
        warnings.simplefilter("always")
        sc = Spheres(scatterers=[Sphere(center=[3e-6, 3e-6, 10e-6], 
                                           n=1.59, r=.5e-6), 
                                    Sphere(center=[3.9e-6, 3.e-6, 10e-6], 
                                           n=1.59, r=.5e-6)])
        assert len(w) > 0
    holo = Multisphere.calc_holo(sc, schema)

    verify(holo, '2_sphere_allow_overlap')

@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_selection():
    sc = Spheres(scatterers=[Sphere(center=[7.1e-6, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07),
                                Sphere(center=[6e-6, 7e-6, 10e-6],
                                       n=1.5811+1e-4j, r=5e-07)])
    schema = ImageSchema(imshape, optics = xoptics)
    subset_schema = ImageSchema(imshape, optics = xoptics, use_random_fraction=.1)
    
    holo = Multisphere.calc_holo(sc, schema, scaling=scaling_alpha)

    subset_holo = Multisphere.calc_holo(sc, subset_schema, scaling=scaling_alpha)

    assert_allclose(subset_holo[subset_schema.selection], holo[subset_schema.selection])

@attr('fast')
@with_setup(setup=setup_model, teardown=teardown_model)
def test_niter():
    sc = Spheres(scatterers=[Sphere(center=[7.1e-6, 7e-6, 10e-6],
                                          n=1.5811+1e-4j, r=5e-07),
                                   Sphere(center=[6e-6, 7e-6, 10e-6],
                                          n=1.5811+1e-4j, r=5e-07)])
    schema = ImageSchema(imshape, optics = xoptics)
    multi = Multisphere(niter = 2)

    assert_raises(ConvergenceFailureMultisphere, multi.calc_holo, sc, schema)

# Copyright 2011, Vinothan N. Manoharan, Thomas G. Dimiduk, Rebecca W. Perry,
# Jerome Fung, and Ryan McGorty
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
The abstract base class for all scattering objects

.. moduleauthor:: Thomas G. Dimiduk <tdimiduk@physics.harvard.edu>
'''
from collections import OrderedDict, defaultdict
from itertools import chain

import numpy as np
import yaml

from holopy.io.yaml_io import Serializable
from scatterpy.errors import ScattererDefinitionError

class Scatterer(Serializable):
    """
    abstract base class for scatterers

    """
    yaml_tag = u'!Scatterer'
    
    def __init__(self):
        raise NotImplementedError

    def validate(self):
        """
        Check that a scatterer is physically realistic.  Theories should call
        this function before attempting computation with a scatterer.  

        Parameters
        ----------
        None

        Returns
        -------
        True is scatterer is valid

        Raises
        ------
        InvalidScatterer or subclass if the scatterer is unphysical for some reason
        """
        # We default to just returning True subclasses that implement overlap
        # checking or other validity constraints override this
        return True


    @property
    def parameters(self):
        """
        Get a dictionary of this scatterer's parameters

        Parameters
        ----------
        None

        Returns
        -------
        parameters: dict
            A dictionary of this scatterer's parameters.  This dict can be
            passed to Scatterer.from_parameters to make a copy of this scatterer
        """

        # classes that have anything complicated happening with their variables
        # should override this, but for simple classes the variable dict is the
        # correct answer

        # we return an OrderedDict to make it easer to keep parameters in the
        # same order in cases where a list of parameters is needed and will be
        # later passed to Scatterer.from_parameters

        def expand(key, par):
            if not np.isscalar(par):
                subs = (expand('{0}[{1}]'.format(key, p[0]), p[1]) for p in enumerate(par)) 
                return chain(*subs)
            if isinstance(par, complex):
                return [('{0}.real'.format(key), par.real),
                        ('{0}.imag'.format(key), par.imag)]
            else:
                return [(key, par)]

        return OrderedDict(sorted(chain(*[expand(*p) for p in
                                          self.__dict__.iteritems()]))) 
    

    @classmethod
    def from_parameters(cls, parameters):
        """
        Create a Scatterer from a dictionary of parameters

        Parameters
        ----------
        parameters: dict or list
            Parameters for a scatterer.  This should be of the form returned by
            Scatterer.parameters.

        Returns
        -------
        scatterer: Scatterer class
            A scatterer with the given parameter values
        """
        # This will need to be overriden for subclasses that do anything
        # complicated with parameters

        collected = defaultdict(dict)

        for key, val in parameters.iteritems():
            tok = key.split('.', 1)
            if len(tok) > 1:
                collected[tok[0]][tok[1]] = val
            else:
                collected[key] = val

        collected_arrays = defaultdict(dict)
        for key, val in collected.iteritems():
            tok = key.split('[', 1)
            if len(key.split('[', 1)) > 1:
                sub_key, n = key.split('[', 1)
                n = int(n[:-1])
                collected_arrays[sub_key][n] = val
            else:
                collected_arrays[key] = val

        built = {}

        def build(par):
            if isinstance(par, dict):
                if sorted(par.keys()) == ['imag', 'real']:
                    return par['real'] + 1.0j * par['imag']
                elif reduce(lambda x, i: isinstance(i, int) and x,
                            par.keys(), True):

                    d = [p[1] for p in sorted(par.iteritems(), key =
                                                 lambda x: x[0])]
                    return [build(p) for p in d]
            return par
            
        for key, val in collected_arrays.iteritems():
            built[key] = build(val)

        return cls(**built)

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, ', '.join(
            ['='.join([str(p) for p in par]) for par in
             sorted(self.__dict__.iteritems())])) 
    

class xyzTriple(np.ndarray):
    """
    
    """
    def __new__(cls, xyz=None):
        if np.isscalar(xyz) or len(xyz) != 3:
            raise InvalidxyzTriple(repr(xyz))
        for i in xyz:
            if i is None:
                raise InvalidxyzTriple(repr(xyz))
        if isinstance(xyz, dict):
            xyz = [xyz['x'], xyz['y'], xyz['z']]


        return np.asarray(xyz).view(cls)

    def __array_finalize__(self, obj):
        pass

    def __array_wrap__(self, out_arr, context=None):
        return np.ndarray.__array_wrap__(self, out_arr, context)


    @property
    def x(self):
        return self[0]
    @property
    def y(self):
        return self[1]
    @property
    def z(self):
        return self[2]
    
    
    @property
    def parameters(self):
        return {'x': self.x, 'y': self.y, 'z': self.z}

    def __str__(self):
        return str(list(self))

class InvalidxyzTriple(Exception):
    def __init__(self, xyz):
       self.xyz = xyz

       
    def __str__(self):
       return ("Specification of xyzTriple({0}) is not valid, should be "
                "specified as (x, y, z)".format(self.xyz))

def xyzTriple_yaml_representer(dumper, data):
    return dumper.represent_scalar(u'!xyzTriple', str(list(data)))
yaml.add_representer(xyzTriple, xyzTriple_yaml_representer)

def xyzTriple_yaml_constructor(loader, node):
    value = loader.construct_scalar(node)
    return xyzTriple(xyz = [float(v) for v in value[1:-1].split(',')])
yaml.add_constructor(u'!xyzTriple', xyzTriple_yaml_constructor)

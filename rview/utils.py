# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016, wradlib Development Team. All Rights Reserved.
# Distributed under the MIT License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
#!/usr/bin/env python

"""
"""

import numpy as np
import matplotlib as mpl
import matplotlib.colors as col

import wradlib as wrl


def wgs84_to_radolan(coords):

    proj_wgs = wrl.georef.epsg_to_osr(4326)
    proj_stereo = wrl.georef.create_osr("dwd-radolan")
    xy = wrl.georef.reproject(coords,
                              projection_source=proj_wgs,
                              projection_target=proj_stereo)
    return xy

def radolan_to_wgs84(coords):

    proj_wgs = wrl.georef.epsg_to_osr(4326)
    proj_stereo = wrl.georef.create_osr("dwd-radolan")
    ll = wrl.georef.reproject(coords,
                              projection_source=proj_stereo,
                              projection_target=proj_wgs)
    return ll


def read_radolan(f, missing=0, loaddata=True):
    return wrl.io.read_RADOLAN_composite(f, missing=missing, loaddata=loaddata)


def cmap_discretize(cmap, N):
     """Return a discrete colormap from the continuous colormap cmap.

   4         cmap: colormap instance, eg. cm.jet.
   5         N: number of colors.
   6
   7     Example
   8         x = resize(arange(100), (5,100))
   9         djet = cmap_discretize(cm.jet, 5)
  10         imshow(x, cmap=djet)
  11     """


     if type(cmap) == str:
         cmap = mpl.cm.get_cmap(cmap)
     colors_i = np.concatenate((np.linspace(0, 1., N), (0.,0.,0.,0.)))
     colors_rgba = cmap(colors_i)
     indices = np.linspace(0, 1., N+1)
     cdict = {}
     for ki,key in enumerate(('red','green','blue')):
         cdict[key] = [ (indices[i], colors_rgba[i-1,ki],
         colors_rgba[i,ki]) for i in range(N+1) ]
     # Return colormap object.
     return col.LinearSegmentedColormap(cmap.name + "_%d"%N, cdict, 1024)





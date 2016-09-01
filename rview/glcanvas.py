# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016, wradlib Development Team. All Rights Reserved.
# Distributed under the MIT License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
#!/usr/bin/env python

"""
"""

import numpy as np
import glob
import netCDF4 as nc

from vispy import scene, visuals
from vispy.util.event import EventEmitter
from vispy.visuals.shaders import Function, FunctionChain
from vispy.color import Color, get_colormap, Colormap
from vispy.visuals.transforms import STTransform

import wradlib as wrl

from rview import utils

def get_cities_coords():

    cities = {}
    cities[u'Köln'] = (6.95, 50.95)   # lat, lon; Unicode fr Umlaute
    cities[u"Hamburg"] = (10.0, 53.55)
    cities[u"Düsseldorf"] = (6.8, 51.2)
    cities[u"Bonn"] = (7.1,50.7)
    cities[u"Frankfurt"] = (8.7,50.1)
    cities[u"Eisenach"] = (10.3, 51.0)
    cities[u"Dresden"]=(13.7,51.1)
    cities[u"Freiburg"]=(7.9,48.0)
    cities[u"Augsburg"]=(10.9, 48.4)
    cities[u"Berlin"]=(13.4,52.5)
    cities[u"München"]=(11.58,48.14)
    cities[u"Jülich"]=(6.46,50.93)

    return cities

class BlackToAlpha(object):
    def __init__(self):
        self.shader = Function("""
            void apply_alpha() {
                const vec3 w = vec3(1, 1, 1);
                float value = dot(gl_FragColor.rgb, w);
                if ( value == 0) {
                    gl_FragColor.a = 0;
                }//if (value == 1) {
                //    gl_FragColor.a = 0;
                //}
            }
        """)

    def _attach(self, visual):
        self._visual = visual
        hook = visual._get_hook('frag', 'post')
        hook.add(self.shader())

_c2l = 'float cmap(vec4 color) { return (color.r + color.g + color.b) / 3.; }'

# self.fshader = Function("""
#     void isoline() {
#         if ($isolevel <= 0 || $isowidth <= 0) {
#             return;
#         }
#
#         // function taken from glumpy/examples/isocurves.py
#         // and extended to have level, width, color and antialiasing
#         // as parameters
#
#         // Extract data value
#         // this accounts for perception,
#         // have to decide, which one to use or make this a uniform
#         //const vec3 w = vec3(0.299, 0.587, 0.114);
#         //#const vec3 w = vec3(0.2126, 0.7152, 0.0722);
#         //float value = dot(gl_FragColor.rgb, w);
#
#         // setup lw, aa
#         //float linewidth = $isowidth + $antialias;
#
#         // "middle" contour(s) dividing upper and lower half
#         // but only if isolevel is even
#         /*
#         if( mod($isolevel,2.0) == 0.0 ) {
#             if( length(value - 0.5) < 0.5 / $isolevel)
#                 linewidth = linewidth * 2;
#         }*/
#
#         // luminance
#         //float lmod = mod(gl_FragColor.r * $isolevel + 0.5, $isolevel);
#         //float lmod = abs(ceil(gl_FragColor.r * $isolevel) / $isolevel);
#         //float lmod = floor(gl_FragColor.r * $isolevel + 0.5) / $isolevel;
#         float lmod = floor(gl_FragColor.r * $isolevel + 0.15) / $isolevel;
#         vec4 lcol = vec4(lmod, lmod, lmod, 1.0);
#
#         // Trace contour isoline
#         /*
#         float v  = $isolevel * value - 0.5;
#         float dv = linewidth/2.0 * fwidth(v);
#         float f = abs(fract(v) - 0.5);
#         float d = smoothstep(-dv, +dv, f);
#         float t = linewidth/2.0 - $antialias;
#         d = abs(d)*linewidth/2.0 - t;
#
#         if( d < - linewidth ) {
#             d = 1.0;
#         } else  {
#              d /= $antialias;
#         }*/
#
#         // setup foreground
#         //vec4 fc = $isocolor;
#
#         // mix with background
#         /*
#         if (d < 1.) {
#             //gl_FragColor = mix(gl_FragColor, fc, 1-d);
#             //gl_FragColor = mix($color_transform(gl_FragColor), fc, 1-d);
#             gl_FragColor = mix($color_transform(lcol), fc, 1-d);
#         } else {
#             gl_FragColor = $color_transform(lcol);
#         }*/
#         gl_FragColor = $color_transform(lcol);
#     }
# """)

class ContourFilter(object):
    def __init__(self, level=2., width=2.0, antialias=1.0, color='black', cmap='cubehelix'):
        self.fshader = Function("""
            void isoline() {
                if ($isolevel <= 0 || $isowidth <= 0 || $antialias < 1.0) {
                    return;
                }

                $antialias;
                vec4 b = $isocolor;

                // luminance
                //float lmod = mod(gl_FragColor.r * $isolevel + 0.5, $isolevel);
                //float lmod = abs(ceil(gl_FragColor.r * $isolevel) / $isolevel);
                //float lmod = floor(gl_FragColor.r * $isolevel + 0.5) / $isolevel;
                float lmod = floor(gl_FragColor.r * $isolevel + 0.15) / $isolevel;
                vec4 lcol = vec4(lmod, lmod, lmod, 1.0);


                gl_FragColor = $color_transform(lcol);
            }
        """)
        self.level = level
        self.width = width
        self.color = color
        self.cmap = cmap
        self.antialias = antialias
        self.isoline_expr = self.fshader()

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, l):
        if l <= 0:
            l = 0
        self._level = l
        self.fshader['isolevel'] = l

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, w):
        self._width = w
        self.fshader['isowidth'] = w

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, c):
        self._color = c
        self.fshader['isocolor'] = Color(c).rgba

    @property
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, cm):
        self._cmap = get_colormap(cm)
        self.fshader['color_transform'] = FunctionChain(None, [Function(_c2l),
                                       Function(self._cmap.glsl_map)])

    @property
    def colortransform(self):
        return self._colortransform

    @color.setter
    def colortransform(self, ct):
        self._colortransform = ct

    @property
    def antialias(self):
        return self._antialias

    @antialias.setter
    def antialias(self, a):
        self._antialias = a
        self.fshader['antialias'] = a

    def _attach(self, visual):
        hook = visual._get_hook('frag', 'post')
        hook.add(self.isoline_expr)


class RadolanCanvas(scene.SceneCanvas):

    def __init__(self):
        scene.SceneCanvas.__init__(self, keys='interactive')
        self.size = 1400, 1300
        self.unfreeze()

        #self.view = self.central_widget.add_view()
        self.grid = self.central_widget.add_grid()

        self.b1 = self.grid.add_view(row=0, col=0)
        self.b1.border_color = (0.5, 0.5, 0.5, 1)
        self.b1.camera = scene.PanZoomCamera(rect=(0,0,1000,900), aspect=1)

        # signal emitters
        self.line_changed = EventEmitter(source=self, type="line_changed")
        self.mouse_moved = EventEmitter(source=self, type="mouse_moved")
        self.events.mouse_double_click.block()

        img_data = np.zeros((900, 900))
        self.X, self.Y = np.meshgrid(np.arange(img_data.shape[0]),np.arange(img_data.shape[1]))

        #cmap = 'grays'
        cmap = 'grays'

        self.image = scene.visuals.Image(img_data, method='impostor', #interpolation='bicubic',
                                         cmap=cmap, parent=self.b1.scene)

        level = 21
        self.iso = ContourFilter(level=level, width=0.01, color='black', cmap=cmap)
        self.image.attach(self.iso)
        #bta = BlackToAlpha()
        #self.image.attach(bta)

        self.cbar = scene.visuals.ColorBar(center_pos=(0, 900), size=np.array([850, 20]),
                                           cmap=cmap, label_str='measurement units', orientation='right',
                                           border_width=1, border_color='white', parent=self.b1.scene)
        self.cbar._colorbar.attach(self.iso)

        self.cbar.label.color = 'white'

        #ticks = [0, 50]
        #self.cbar.clim = (1,0)
        for tick in self.cbar.ticks:
            tick.color = 'white'


        self.image.transform = visuals.transforms.STTransform(translate=(0, 0, 60))
        self.image.visible = True
        self.cbar.transform = visuals.transforms.STTransform(scale=(1, -1, 1), translate=(940, 450, 0.5))

        self.line = None
        radolan = wrl.georef.get_radolan_grid()
        self.r0 = radolan[0,0]
        self.create_cities()

        self.cam = scene.cameras.PanZoomCamera(name="PanZoom", parent=self.b1.scene, rect=(0,0,1000,900), aspect=1)
        self.b1.camera = self.cam
        self.view = self.b1

        self.vline = scene.visuals.Line(parent=self.b1.scene, color="darkgrey")
        self.vline.transform = visuals.transforms.STTransform(translate=(0, 0, -2.5))
        self.hline = scene.visuals.Line(parent=self.b1.scene, color="darkgrey")
        self.hline.transform = visuals.transforms.STTransform(translate=(0, 0, -2.5))
        self.cursor_text = scene.visuals.Text('', bold=False, parent=self.b1.scene,
                                              font_size=10,
                                              anchor_x='left', anchor_y='bottom')

        self.vline.visible = False
        self.hline.visible = False
        self.cursor_text.visible = False

        self.measure_fps()

    def create_cities_flipped(self):
        # initialize citie markers
        self.markers = scene.visuals.Markers(parent=self.b1.scene)
        cities = get_cities_coords()
        cnameList = []
        ccoordList = []
        for k, v in cities.items():
            cnameList.append(k)
            ccoordList.append(v)
        ccoord = np.vstack(ccoordList)
        ccoord = utils.wgs84_to_radolan(ccoord)
        radolan = wrl.georef.get_radolan_grid()
        #print(radolan[...,0].shape)
        x0 = np.flipud(radolan[...,0])
        y0 = np.flipud(radolan[...,1])
        #print()
        r0 = radolan[0,0]
        #print(r0)
        pos_scene = np.zeros((ccoord.shape[0], 2), dtype=np.float32)
        #print(pos_scene.shape)
        pos_scene[:,1] = 900 - (ccoord[:,1] - r0[1])
        pos_scene[:,0] = (ccoord[:,0] - r0[0])
        #print(pos_scene)
        self.markers.set_data(pos=pos_scene, symbol="s", edge_color="blue",
                              size=20)
        self.text = scene.visuals.Text(text=cnameList, pos=pos_scene, font_size=40,
                                       anchor_x = 'right', anchor_y = 'top', parent=self.b1.scene)


    def create_cities(self):
        # initialize citie markers
        self.markers = scene.visuals.Markers(parent=self.b1.scene)
        cities = get_cities_coords()
        cnameList = []
        ccoordList = []
        for k, v in cities.items():
            cnameList.append(k)
            ccoordList.append(v)
        ccoord = np.vstack(ccoordList)
        ccoord = utils.wgs84_to_radolan(ccoord)
        radolan = wrl.georef.get_radolan_grid()
        #r0 = radolan[0,0]
        pos_scene = np.zeros((ccoord.shape[0], 2), dtype=np.float32)
        pos_scene[:] = ccoord - self.r0
        self.markers.set_data(pos=pos_scene, symbol="disc", edge_color="blue",
                              size=10)
        self.text = scene.visuals.Text(text=cnameList, pos=pos_scene, font_size=20,
                                       anchor_x = 'right', anchor_y = 'top', parent=self.b1.scene)

    def set_colormap(self, cmap):
        self.image.cmap = cmap
        self.cbar.cmap = cmap
        #zhcmap = ['#ffffff','#092faa','#174ef8','#27b4f3','#35edee','#33f64b','#25ca39',
        #  '#17a029','#057217','#fef858','#fece4b','#fda540','#fc7a36','#fd2e2e',
        #  '#e12826','#bf1f1d','#9f1713','#fd5bfa','#a675ce','#5e46a3','#421d74']#, '#421d74']

        #levels = [-10,-6,-2,0,3,8,10,12,15,18,20,24,26,28,30,34,38,42,48,53,58,65]

        #def scale(val, src, dst):
        #    """
        #    Scale the given value from the scale of src to the scale of dst.
        #    """
        #    return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]

        #lm = scale(np.asarray(levels, dtype=np.float), (-10, 65), (0,1))
        #print(lm)
        #print(lm.shape)

        #cm2 = Colormap(zhcmap[::-1], controls=lm, interpolation='zero')
        #self.iso.cmap = cm2
        self.iso.cmap = cmap

    def set_data(self, n_levels, cmap):
        #self.iso.set_color(cmap)
        #cl = np.linspace(-self.radius, self.radius, n_levels + 2)[1:-1]
        #self.iso.levels = cl
        pass

    def print_mouse_event(self, event, what):
        """ print mouse events for debugging purposes """
        print('%s - pos: %r, button: %s,  delta: %r' %
              (what, event.pos, event.button, event.delta))

    def on_mouse_move(self, event):
        #pass
        point = self.scene.node_transform(self.image).map(event.pos)[:2]
        #point[1] = 900 - point[1]
        self._mouse_position = point
        self.mouse_moved()
        self.update_cursor(point)
        #self.update_cursor(event.pos)

    def update_cursor(self, pos):

        if self.hline.visible and self.vline.visible:
            ll = utils.radolan_to_wgs84(pos + self.r0)
            self.cursor_text.text = '({0:3.3f}, {1:3.3f})'.format(ll[0], ll[1])
            self.cursor_text.pos = pos + (0, 0)

        self.vline.set_data(np.array([[pos[0], 0], [pos[0], 899]]))
        self.hline.set_data(np.array([[0, pos[1]], [899, pos[1]]]))




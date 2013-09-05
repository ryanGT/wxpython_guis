from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')

import sys, time, os, gc
import matplotlib
matplotlib.use('WXAgg')
import matplotlib.cm as cm
import matplotlib.cbook as cbook
from matplotlib.backends.backend_wxagg import Toolbar, FigureCanvasWxAgg
from matplotlib.figure import Figure
import numpy as np

import wx
import wx.xrc as xrc

import wx.grid


class PlotPanel(wx.Panel):

    def __init__(self, parent, fig_size=(8,6)):
        wx.Panel.__init__(self, parent, -1)

        self.fig = Figure(fig_size, 100)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.toolbar = Toolbar(self.canvas) #matplotlib toolbar
        self.toolbar.Realize()
        #self.toolbar.set_active([0,1])

        # Now put all into a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        # This way of adding to sizer allows resizing
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        # Best to allow the toolbar to resize!
        sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()


    def init_plot_data(self):
        a = self.fig.add_subplot(111)
        t = np.arange(0,1,0.01)
        y = np.sin(2*np.pi*t)
        self.lines = a.plot(t,y)
        self.ax = a
        self.toolbar.update() # Not sure why this is needed - ADS


    def change_plot(self):
        self.ax.clear()
        t = np.arange(0,1,0.01)
        y2 = np.cos(2*np.pi*t)
        self.ax.plot(t,y2)
        self.canvas.draw()


    def GetToolBar(self):
        # You will need to override GetToolBar if you are using an
        # unmanaged toolbar in your frame
        return self.toolbar

    ## def OnWhiz(self,evt):
    ##     self.x += np.pi/15
    ##     self.y += np.pi/20
    ##     z = np.sin(self.x) + np.cos(self.y)
    ##     self.im.set_array(z)

    ##     zmax = np.amax(z) - ERR_TOL
    ##     ymax_i, xmax_i = np.nonzero(z >= zmax)
    ##     if self.im.origin == 'upper':
    ##         ymax_i = z.shape[0]-ymax_i
    ##     self.lines[0].set_data(xmax_i,ymax_i)

    ##     self.canvas.draw()

    def onEraseBackground(self, evt):
        # this is supposed to prevent redraw flicker on some X servers...
        pass


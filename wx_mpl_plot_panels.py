from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')#<-- you can only do this in top-level modules or scripts

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
    """This example is from something I found on the matplotlib
    webpage.  They combined an embedded mpl plot with the wxPython xrc
    approach.  They basically create a wx.Panel placeholder in the xrc
    file.  See data_vis_gui.py for an example of using this class.

    Your really don't need anything other than the __init__ method.
    After that, just grab :py:attr:`self.fig` and use the matplotlib
    methods of the figure instance (the object-oriented API, not
    pylab)."""
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
        """This just creates the starting graph."""
        a = self.fig.add_subplot(111)
        t = np.arange(0,1,0.01)
        y = np.sin(2*np.pi*t)
        self.lines = a.plot(t,y)
        self.ax = a
        self.toolbar.update() # Not sure why this is needed - ADS


    def change_plot(self):
        """This is just a method to show I can update the plot from a
        program.  It doesn't really do anything else useful.  It
        serves as an example of clearing the axis, plotting something,
        and refreshing the graph."""
        self.ax.clear()
        t = np.arange(0,1,0.01)
        y2 = np.cos(2*np.pi*t)
        self.ax.plot(t,y2)
        self.canvas.draw()


    def GetToolBar(self):
        """This is from the example; I don't know what it does."""
        # You will need to override GetToolBar if you are using an
        # unmanaged toolbar in your frame
        return self.toolbar


    def onEraseBackground(self, evt):
        """I don't know what this does either (based on the comment
        below, I guess it prevents flicker)."""
        # this is supposed to prevent redraw flicker on some X servers...
        pass


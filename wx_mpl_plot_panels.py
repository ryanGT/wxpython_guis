from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')#<-- you can only do this in top-level modules or scripts

import sys, time, os, gc
import rwkos

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



xrc_folder = rwkos.FindFullPath('git/wxpython_guis')
pp_filename = 'plot_panel_with_bd_side_panel.xrc'
pp_xrc_path = os.path.join(xrc_folder, pp_filename)


class plot_panel_with_bd_side_panel(wx.Panel):
    def on_refresh_plot(self, event):
        legloc = int(self.legloc_textctrl.GetValue())
        mylist = self.get_plot_list()
        self.plot_method(mylist, clear=True, legloc=legloc)


    def on_popup_item_selected(self, event):
        item = self.popupmenu.FindItemById(event.GetId())
        text = item.GetText()
        #wx.MessageBox("You selected item '%s'" % text)
        self.popup_choice = text


    def create_popup_menu(self, include_delete=False):
        self.popupmenu = wx.Menu()
        self.popup_choice = None

        blocks = [block.name for block in self.bd_parent.blocklist]

        if include_delete:
            delete_item = self.popupmenu.Append(-1, 'delete')
            self.Bind(wx.EVT_MENU, self.on_popup_item_selected, delete_item)
            self.popupmenu.AppendSeparator()

            
        for block in blocks:
            menu_item = self.popupmenu.Append(-1, block)
            self.Bind(wx.EVT_MENU, self.on_popup_item_selected, menu_item)



    def show_popup_menu(self, event):
        print('in show_popup_menu')
        col = event.GetCol()
        row = event.GetRow()
        print('col = %s' % col)
        print('row = %s' % row)
        attr = self.signals_grid.GetCellValue(row,0)
        attr = attr.strip()

        delete_bool = False
        if attr:
            delete_bool = True
            
        self.create_popup_menu(include_delete=delete_bool)
            

        result = self.PopupMenu(self.popupmenu)#, pos)
        print('result = %s' % result)
        
        if result and hasattr(self, 'popup_choice'):
            if self.popup_choice:
                if self.popup_choice == 'delete':
                    self.signals_grid.DeleteRows(row, 1)
                    self.signals_grid.AppendRows(1)
                else:
                    self.signals_grid.SetCellValue(row, 0, self.popup_choice)


    def get_plot_list(self):
        """Build a list of 3-tuples where the first element is the
        name of the block, the second is the column index, and the
        third is the label.  Do this for each row in self.signals_grid"""
        mylist = []

        max_rows = 30

        for i in range(max_rows):
            block_name = self.signals_grid.GetCellValue(i,0)
            if not block_name:
                break

            col = self.signals_grid.GetCellValue(i,2)
            if not col:
                col = 0
            else:
                col = int(col)

            label = self.signals_grid.GetCellValue(i,1)
            if not label:
                label = None

            cur_row = (block_name, col, label)
            mylist.append(cur_row)

        return mylist
    
            
    def get_fig(self):
        return self.plotpanel.fig
        
        
    def draw(self):
        self.plotpanel.canvas.draw()
        
        
    def __init__(self, parent, bd_parent, plot_method):
        """I am trying to deal with the idea that a modular block
        diagram GUI still needs to have only one blocklist that every
        panel can access.  My approach is to have the parent
        application contain the blocklist.  The problem is that in the
        wxPython GUI since, the parent of a panel might be another
        panel or a notebook or whatever.  So, bd_parent is my own
        paramenter that refers to the block diagram parent,
        i.e. whatever contains the actual blocklist."""
        pre = wx.PrePanel()
        res = xrc.XmlResource(pp_xrc_path)
        res.LoadOnPanel(pre, parent, "main_panel") 
        self.PostCreate(pre)
        self.parent = parent
        
        self.plot_method = plot_method

        plot_container = xrc.XRCCTRL(self, "plot_panel")
        sizer = wx.BoxSizer(wx.VERTICAL)

        # matplotlib panel itself
        self.plotpanel = PlotPanel(plot_container, fig_size=(6,5))
        self.plotpanel.init_plot_data()

        self.signals_grid = xrc.XRCCTRL(self, "signals_grid")
        self.signals_grid.CreateGrid(10,3)
        self.signals_grid.SetRowLabelSize(30)
        self.signals_grid.SetColLabelValue(0,'Block')
        self.signals_grid.SetColLabelValue(1,'Label')
        self.signals_grid.SetColLabelValue(2,'Index')

        self.signals_grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK,
                               self.show_popup_menu)


        self.legloc_textctrl = xrc.XRCCTRL(self, "legloc_textctrl")

        self.refresh_button = xrc.XRCCTRL(self, "refresh_button")
        wx.EVT_BUTTON(self.refresh_button, self.refresh_button.GetId(),
                      self.on_refresh_plot)

        
        self.bd_parent = bd_parent
        assert hasattr(self.bd_parent, 'blocklist'), \
               "The parent of a tikz_viewer_panel must have a blocklist attribute"       



from __future__ import print_function

# Used to guarantee to use at least Wx2.8
import wxversion
wxversion.ensureMinimal('2.8')

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

import wx_mpl_plot_panels as WMPP
import txt_data_processing
import copy
import pdb

data_wildcard = "Text files (*.txt; *.csv)|*.txt;*.csv|" \
                "All files (*.*)|*.*"


class MyGridTable(wx.grid.PyGridTableBase):
    def __init__(self, data):
        wx.grid.PyGridTableBase.__init__(self)
        self.data = data
        
    def GetNumberRows(self):
        """Return the number of rows in the grid"""
        return len(self.data)

    def GetNumberCols(self):
        """Return the number of columns in the grid"""
        row0 = self.data[0]
        return len(row0)

    def IsEmptyCell(self, row, col):
        """Return True if the cell is empty"""
        return False

    def GetTypeName(self, row, col):
        """Return the name of the data type of the value in the cell"""
        return type(self.data[row][col])

    def GetValue(self, row, col):
        """Return the value of a cell"""
        return self.data[row][col]

    def SetValue(self, row, col, value):
        """Set the value of a cell"""
        self.data[row][col] = value


class plot_description(object):
    """This class will be used to determine how to plot a certain data
    file and ultimately how to save that plot description as an XML
    file."""
    def remove_n_and_t_from_plot_labels(self):
        i = 0
        while i < len(self.plot_labels):
            label = self.plot_labels[i]
            if label in ['n','t']:
                self.plot_labels.pop(i)
            else:
                i += 1


    def __init__(self, datapath, plot_labels=None, legend_dict={}, \
                 legloc=1):
        self.datapath = datapath
        self.plot_labels = plot_labels
        self.legend_dict = legend_dict
        self.df = txt_data_processing.Data_File(datapath)
        self.data = self.df.data
        self.labels = self.df.labels
        if plot_labels is None:
            self.plot_labels = copy.copy(self.labels)
            self.remove_n_and_t_from_plot_labels()
        self.legend_dict = legend_dict
        self.legloc = legloc
        

    def create_lable_str(self):
        label_str = ''
        first = True

        for label in self.plot_labels:
            if first:
                first = False
            else:
                label_str += ', '
            label_str += label

        return label_str


    def plot(self, ax, clear=False):
        self.df.Time_Plot(labels=self.plot_labels, ax=ax, clear=clear, \
                          legloc=self.legloc, legend_dict=self.legend_dict, \
                          )
        ## ylabel='Voltage (counts)', \
        ## basename=None, save=False, \
        ## ext='.png', fig_dir='', title=None, \
        ## linetypes=None, \
        ## **plot_opts)


    def _create_legend_dict(self):
        self.legend_dict = dict(zip(self.plot_labels, self.plot_labels))
        

    def create_legend_str(self):
        if not self.legend_dict:
            self._create_legend_dict()
        leg_str = ''
        first = True

        for key, val in self.legend_dict.iteritems():
            if first:
                first = False
            else:
                leg_str += ', '
            leg_str += '%s:%s' % (key, val)

        return leg_str
        
    
class MyApp(wx.App):
    def plot_already_loaded(self):
        pass

        
    def get_axis(self):
        fig = self.plotpanel.fig
        if len(fig.axes) == 0:
            ax = fig.add_subplot(111)
        else:
            ax = fig.axes[0]
        return ax

        
    def plot_cur_df(self):
        ax = self.get_axis()
        ax.clear()
        self.cur_plot_description.plot(ax)
        self.plotpanel.canvas.draw()


    def set_labels_ctrl(self):
        label_str = self.cur_plot_description.create_lable_str()
        self.label_text_ctrl.SetValue(label_str)


    def set_legend_str(self):
        legend_str = self.cur_plot_description.create_legend_str()
        self.legend_dict_ctrl.SetValue(legend_str)


    def get_label_str(self):
        return self.label_text_ctrl.GetValue()


    def get_legend_str(self):
        return self.legend_dict_ctrl.GetValue()


    def parse_label_str(self):
        label_list = self.get_label_str().split(',')
        plot_labels = [label.strip() for label in label_list]
        return plot_labels


    def parse_legend_str(self):
        legend_list = self.get_legend_str().split(',')
        legend_dict = {}
        
        for cur_str in legend_list:
            key, val = cur_str.split(':',1)
            key = key.strip()
            val = val.strip()
            val = val.replace('\\\\','\\')
            legend_dict[key] = val

        return legend_dict
    
        
    def load_data_file(self, datapath):
        self.cur_plot_description = plot_description(datapath)
        cpd = self.cur_plot_description
        print('shape = %s, %s' % cpd.data.shape)
        self.set_labels_ctrl()
        self.set_legend_str()
        self.data = [cpd.labels] + cpd.data.tolist()
        self.table = MyGridTable(self.data)
        self.preview_grid.SetTable(self.table)
        self.plot_cur_df()


    def on_update_plot(self, event):
        print('in on_update_plot')        
        labels = self.parse_label_str()
        self.cur_plot_description.plot_labels = labels
        legend_dict = self.parse_legend_str()
        self.cur_plot_description.legend_dict = legend_dict
        legloc = int(self.legloc_ctrl.GetValue())
        self.cur_plot_description.legloc = legloc
        self.plot_cur_df()

        
    def on_add_file(self, event):
        """
        Create and show the Open FileDialog
        """
        print('in on_add_file')
        filename = None
        dirname = None
        
        dlg = wx.FileDialog(self.frame, message="Choose a file",
                            defaultFile="",
                            wildcard=data_wildcard,
                            style=wx.OPEN | wx.CHANGE_DIR
                            )
        
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            self.file_name_ctrl.SetValue(filename)
            self.folder_ctrl.SetValue(dirname)
            self.datapath = os.path.join(dirname, filename)
            self.load_data_file(self.datapath)
            self.preview_grid.Refresh()
        dlg.Destroy()

        
        return filename, dirname

     
    def OnInit(self):
        #xrcfile = cbook.get_sample_data('ryans_first_xrc.xrc', asfileobj=False)
        xrcfile = 'data_vis_xrc.xrc'
        print('loading', xrcfile)

        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        ## self.panel = xrc.XRCCTRL(self.frame,"MainPanel")
        ## self.new_element_choice = xrc.XRCCTRL(self.frame, "new_element_choice")
        ## self.new_element_choice.SetItems(sorted_elements)
        self.add_file_button = xrc.XRCCTRL(self.frame,"add_file")
        self.update_plot_button = xrc.XRCCTRL(self.frame, "update_plot_button")
        self.folder_ctrl = xrc.XRCCTRL(self.frame, "folder_ctrl")
        self.file_name_ctrl = xrc.XRCCTRL(self.frame, "file_name_ctrl")
        wx.EVT_BUTTON(self.add_file_button, self.add_file_button.GetId(),
                      self.on_add_file)
        wx.EVT_BUTTON(self.update_plot_button, self.update_plot_button.GetId(),
                      self.on_update_plot)
        self.label_text_ctrl = xrc.XRCCTRL(self.frame, "label_text_ctrl")
        self.legend_dict_ctrl = xrc.XRCCTRL(self.frame, "legend_dict_ctrl")
        self.legloc_ctrl = xrc.XRCCTRL(self.frame, "legloc_ctrl")
        self.legloc_ctrl.SetValue("1")
        #pdb.set_trace()
        self.menubar = self.frame.GetMenuBar()
        self.frame.Bind(wx.EVT_MENU, self.on_add_file, id=xrc.XRCID('add_file_menu'))
        self.frame.Bind(wx.EVT_MENU, self.on_update_plot, id=xrc.XRCID('update_plot_menu')) 
        ## add_file_menu = self.menubar.FindItemById(xrc.XRCID('add_file_menu'))
        ## add_file_menu.Bind(wx.EVT_MENU, self.on_add_file)#, add_file_menu)
        ## update_plot_menu = self.menubar.FindItemById(xrc.XRCID('update_plot_menu'))
        ## update_plot_menu.Bind(wx.EVT_MENU, self.on_update_plot)#, update_plot_menu)
        
        ## wx.EVT_CHOICE(self.new_element_choice, self.new_element_choice.GetId(),
        ##               self.on_new_element_choice)

        ## self.load_button = xrc.XRCCTRL(self.frame, "load_button")
        ## wx.EVT_BUTTON(self.load_button, self.load_button.GetId(),
        ##               self.on_load_button)
        ## self.save_button = xrc.XRCCTRL(self.frame, "save_button")
        ## wx.EVT_BUTTON(self.save_button, self.save_button.GetId(),
        ##               self.on_save_button)
        self.preview_grid = xrc.XRCCTRL(self.frame, "preview_grid")
        data = np.zeros((10,10))
        mytable = MyGridTable(data)
        self.data = data
        self.preview_grid.SetTable(mytable)
        self.table = mytable
        ## self.preview_grid.CreateGrid(5,10)

        ## for i in range(5):
        ##     for j in range(10):
        ##         self.preview_grid.SetCellValue(i,j, str(i*j))



        plot_container = xrc.XRCCTRL(self.frame,"plot_panel")
        sizer = wx.BoxSizer(wx.VERTICAL)

        # matplotlib panel itself
        self.plotpanel = WMPP.PlotPanel(plot_container, fig_size=(7,4))
        self.plotpanel.init_plot_data()

        # wx boilerplate
        sizer.Add(self.plotpanel, 1, wx.EXPAND)
        plot_container.SetSizer(sizer)
        #self.plotpanel.SetMinSize((900,600))

        self.frame.SetClientSize((1200,700))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()




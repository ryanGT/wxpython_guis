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
xml_wildcard = "XML files (*.xml)|*.xml"


import xml.etree.ElementTree as ET
from xml.dom import minidom

import xml_utils
from xml_utils import prettify

import wx_utils

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


def parse_one_pd(pd_xml):
    assert pd_xml.tag == 'plot_description', \
           "Child is not a valid plot_description xml chunk."
    string_dict = xml_utils.children_to_dict(pd_xml)
    out_dict = copy.copy(string_dict)
    out_dict['plot_labels'] = xml_utils.list_string_to_list(out_dict['plot_labels'])
    out_dict['legend_dict'] = xml_utils.dict_string_to_dict(out_dict['legend_dict'])
    return out_dict


class plot_description_file_parser(xml_utils.xml_parser):
    """This parser will parse a file that may contain a list of
    plot_description items."""
    def parse(self):
        assert self.root.tag == 'plot_description_file', \
               "This does not appear to be a valide plot_description_file."
        self.pd_xml_list = self.root.getchildren()
        self.parsed_dicts = [parse_one_pd(item) for item in self.pd_xml_list]


    def convert(self):
        self.pd_list = [plot_description(**kwargs) for kwargs in self.parsed_dicts]
        return self.pd_list
    
         
    ## def __init__(self, filename):
    ##     xml_utils.xml_parser.__init__(self, filename)
        

class figure_parser(plot_description_file_parser):
    """Parse an xml file containing a single figure."""
    def validate_and_get_body(self):
        if self.root.tag in ['time_domain_figure', 'bode_figure']:
            body = self.root
            return body
        elif self.root.tag == 'figure':
            children = self.root.getchildren()
            #a figure file should have one child that is either a
            #bode_figure or a time_domain_figure
            assert len(children) == 1, "problem with the children in my xml file"
            body = children[0]
            return body
        else:
            raise ValueError, "Not sure how to proceed for a figure with tag %s" % self.root.tag
        
    def parse(self):
        body = self.validate_and_get_body()
        self.class_name = body.tag
        if self.class_name == 'time_domain_figure':
            self.myclass = time_domain_figure
        elif self.class_name == 'bode_figure':
            self.myclass = bode_figure
        else:
            raise ValueError, \
                  "Not sure what to do with figure type %s" % self.class_name
        name_xml = xml_utils.find_child(body, 'name')
        self.name = name_xml.text.strip()
        
        self.pd_xml_list = xml_utils.find_child(body, 'plot_description_list')
        self.parsed_dicts = [parse_one_pd(item) for item in self.pd_xml_list]

        params_xml = xml_utils.find_child(body, 'params')
        self.params = xml_utils.children_to_dict(params_xml)


    def convert(self):
        plot_description_file_parser.convert(self)
        fig_instance = self.myclass(self.name, self.pd_list, **self.params)
        return fig_instance
    

class gui_state_parser(plot_description_file_parser):
    """class to parse a GUI state from xml"""
    def get_plot_descriptions(self):
        self.pd_xml_list = xml_utils.find_child(self.root, 'plot_description_list')


    def get_params(self):
        self.params_xml = xml_utils.find_child(self.root, 'gui_params')


    def get_figures(self):
        self.fig_xml_list = xml_utils.find_child_if_it_exists(self.root, \
                                                              'figures')

    
    def parse(self):
        assert self.root.tag == 'data_vis_gui_state', \
               "This does not appear to be a valid data_vis_gui_state"
        self.get_plot_descriptions()
        self.parsed_dicts = [parse_one_pd(item) for item in self.pd_xml_list]
        self.get_params()
        self.params = xml_utils.children_to_dict(self.params_xml)
        self.params['selected_inds'] = xml_utils.list_string_to_list(self.params['selected_inds'])
        self.has_figs = False
        self.get_figures()
        if self.fig_xml_list is not None:
            self.has_figs = True
            fig_parsers = []
            for fig_xml in self.fig_xml_list:
                cur_parser = figure_parser(filename=None)
                cur_parser.set_root(fig_xml)
                cur_parser.parse()
                fig_parsers.append(cur_parser)
                
            self.fig_parsers = fig_parsers

        
    def convert(self):
        plot_description_file_parser.convert(self)
        if self.has_figs:
            fig_list = []
            for fig_parser in self.fig_parsers:
                cur_fig = fig_parser.convert()
                fig_list.append(cur_fig)

            self.fig_list = fig_list
            


class plot_description(xml_utils.xml_writer):
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


    def __init__(self, datapath, name='', plot_labels=None, legend_dict={}, \
                 legloc=1, bode_input_str=None, bode_output_str=None):
        self.datapath = datapath
        self.name = name
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
        self.bode_input_str = bode_input_str
        self.bode_output_str = bode_output_str
        self.xml_tag_name = 'plot_description'
        self.xml_attrs = ['name','datapath','plot_labels','legend_dict', \
                          'bode_input_str','bode_output_str']
        

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


    def bode_plot(self, fig, **kwargs):
        self.df.bode_plot(inlabel=self.bode_input_str, \
                          outlabel=self.bode_output_str, \
                          clear=False, \
                          fig=fig, **kwargs)
        

class figure(xml_utils.xml_writer):
    """Figures will be used to allow my app to switch quickly between
    different sets of plotted data in a way that is analagous to
    tabbing between different figures when using pylab/ipython.

    Each figure instance needs to contain enough information to plot
    one figure."""
    def __init__(self, name, plot_descriptions, plot_type, **kwargs):
        self.name = name
        self.plot_descriptions = plot_descriptions
        self.plot_type = plot_type
        for key, val in kwargs.iteritems():
            setattr(self, key, val)


    def create_xml(self, root):
        fig_root = ET.SubElement(root, self.xml_tag_name)
        dict1 = {'name':self.name}
        xml_utils.append_dict_to_xml(fig_root, dict1)
        pd_list_xml = ET.SubElement(fig_root, 'plot_description_list')

        for pd in self.plot_descriptions:
            pd.create_xml(pd_list_xml)

        if self.xml_params:
            params_xml = ET.SubElement(fig_root, 'params')
            for attr in self.xml_params:
                cur_xml = ET.SubElement(params_xml, attr)
                attr_str = str(getattr(self, attr))
                cur_xml.text = attr_str.encode()


class time_domain_figure(figure):
    def __init__(self, name, plot_descriptions, xlim=None, ylim=None, \
                 ylabel=None, xlabel=None):
        figure.__init__(self, name, plot_descriptions, plot_type='time', \
                        xlim=xlim, ylim=ylim, \
                        xlabel=xlabel, ylabel=ylabel)
        self.xml_tag_name = 'time_domain_figure'
        self.xml_params = ['xlim','ylim','ylabel','xlabel']
        

class bode_figure(figure):
    def __init__(self, name, plot_descriptions, \
                 freqlim=None, maglim=None, phaselim=None):
        figure.__init__(self, name, plot_descriptions, plot_type='bode', \
                        freqlim=freqlim, maglim=maglim, phaselim=phaselim)
        self.xml_tag_name = 'bode_figure'
        self.xml_params = ['freqlim','maglim','phaselim']


class figure_dialog(wx.Dialog):
    def __init__(self, parent):
        pre = wx.PreDialog() 
        self.PostCreate(pre)
        res = xrc.XmlResource('figure_name_dialog.xrc')
        res.LoadOnDialog(self, None, "main_dialog") 

        self.Bind(wx.EVT_BUTTON, self.on_ok, xrc.XRCCTRL(self, "ok_button")) 
        self.Bind(wx.EVT_BUTTON, self.on_cancel, xrc.XRCCTRL(self, "cancel_button"))

        self.figure_name_ctrl = xrc.XRCCTRL(self, "figure_name_ctrl")
        self.figure_number_ctrl = xrc.XRCCTRL(self, "figure_number_ctrl")


    def on_ok(self, event):
        self.EndModal(wx.ID_OK)


    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)
        
        
        #wx.Dialog.__init__(self, parent)
        #sizer = wx.FlexGridSizer(3,2,5,2)
        #label1 = wx.StaticText(self, label='Figure Name:')
        #sizer.Add(label1, 0, wx.ALIGN_RIGHT|wx.LEFT, 5)
        
        ## sizer =  self.CreateTextSizer('My Buttons')
        ## sizer.Add(wx.Button(self, -1, 'Button'), 0, wx.ALL, 5)
        ## sizer.Add(wx.Button(self, -1, 'Button'), 0, wx.ALL, 5)
        ## sizer.Add(wx.Button(self, -1, 'Button'), 0, wx.ALL, 5)
        ## sizer.Add(wx.Button(self, -1, 'Button'), 0, wx.ALL|wx.ALIGN_CENTER, 5)
        ## sizer.Add(wx.Button(self, -1, 'Button'), 0, wx.ALL|wx.EXPAND, 5)
        ##self.SetSizer(sizer)
        
    
class MyApp(wx.App):
    def get_plot_description_ind(self, pd):
        items = self.plot_name_list_box.GetItems()
        key = pd.name
        ind = items.index(key)
        return ind


    def get_plot_description_inds(self, pd_list):
        ind_list = [self.get_plot_description_ind(pd) for pd in pd_list]
        return ind_list

    
    def set_selected_plot_descriptions(self, pd_list):
        self.plot_name_list_box.DeselectAll()
        ind_list = self.get_plot_description_inds(pd_list)
        for ind in ind_list:
            self.plot_name_list_box.Select(ind)



    def find_fig_ind(self, fig_name):
        found = 0
        for i, fig in enumerate(self.figure_list):
            if fig.name == fig_name:
                found = 1
                return i
            
        if not found:
            return None

        
    def set_active_figure(self, ind):
        print('in set_active_figure')
        self.active_fig = self.figure_list[ind]
        self.set_selected_plot_descriptions(self.active_fig.plot_descriptions)

        if type(self.active_fig) == time_domain_figure:
            sel = 0
        elif type(self.active_fig) == bode_figure:
            sel = 1
        self.td_bode_notebook.SetSelection(sel)

        self._update_plot()


    def on_switch_to_bode(self,event):
        self.td_bode_notebook.SetSelection(1)
        #feature: how to check for bode readiness?
        #
        # - non-empty input and output text boxes?
        # - first active figure has bode input and output defined?


    def on_switch_to_time_domain(self,event):
        self.td_bode_notebook.SetSelection(0)
        self._update_plot()
        
        
    def change_fig(self, event):
        eid = event.GetId()
        print('in change_fig, Id=%s' % eid)
        ind = self.figure_menu_ids.index(eid)
        print('ind = %i' % ind)
        self.set_active_figure(ind)
        

       
    def plot_already_loaded_td(self):
        for key in self.plot_list:
            pd = self.plot_dict[key]
            self.plot_time_domain(pd, clear=False)


    def plot_already_loaded_bode(self):
        for key in self.plot_list:
            pd = self.plot_dict[key]
            self.plot_bode(pd)

        
    def get_axis(self):
        fig = self.plotpanel.fig
        if len(fig.axes) == 0:
            ax = fig.add_subplot(111)
        else:
            ax = fig.axes[0]
        return ax


    def get_fig(self):
        fig = self.plotpanel.fig
        return fig


    def plot_time_domain(self, plot_descript, clear=False, draw=True):
        fig = self.get_fig()
        if clear:
            fig.clf()
        ax = self.get_axis()
        plot_descript.plot(ax)
        if draw:
            self.plotpanel.canvas.draw()



    def plot_inds(self, inds, plot_method):
        for ind in inds:
            key = self.plot_list[ind]
            pd = self.plot_dict[key]
            plot_method(pd, clear=False, draw=False)
        self.plotpanel.canvas.draw()

        
    def plot_td(self, inds):
        self.plot_inds(inds, self.plot_time_domain)
        

    def get_selected_plot_inds(self):
        all_items = self.plot_name_list_box.GetItems()
        inds = self.plot_name_list_box.GetSelections()
        return inds

    def clear_fig(self):
        fig = self.get_fig()
        fig.clf()

        
    def plot_all_td(self):
        self.clear_fig()
        inds = self.get_selected_plot_inds()
        if len(inds) > 0:
            self.plot_td(inds)


    def plot_all_bode(self):
        self.clear_fig()
        inds = self.get_selected_plot_inds()
        if len(inds) > 0:
            self.plot_bodes(inds)


    def plot_bodes(self, inds):
        self.plot_inds(inds, self.plot_bode)
        
        
    def plot_cur_df(self, clear=False):
        self.plot_time_domain(self.cur_plot_description, clear=clear)


    def plot_bode(self, plot_descript, clear=True, draw=True):
        fig = self.get_fig()
        if clear:
            fig.clf()
        plot_descript.bode_plot(fig)
        if draw:
            self.plotpanel.canvas.draw()


    def plot_cur_bode(self, clear=False):
        self.plot_bode(self.cur_plot_description, clear=clear)


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
    
        
    def load_data_file(self, datapath, name=''):
        self.cur_plot_description = plot_description(datapath, name)
        cpd = self.cur_plot_description
        print('shape = %s, %s' % cpd.data.shape)
        self.set_labels_ctrl()
        self.set_legend_str()
        self.data = [cpd.labels] + cpd.data.tolist()
        self.table = MyGridTable(self.data)
        self.preview_grid.SetTable(self.table)
        #self.plot_all_td()
        #self.plot_cur_df()


    def _update_plot(self):
        """Simply plot the time domain or Bode plots without updating
        the GUI or checking for changes in labels or legend stuff.  To
        be used after loading xml files or in other instances where
        the GUI was just set programmatically and the plot needs to be
        redrawn."""
        sel = self.td_bode_notebook.GetSelection()
        if sel == 0:
            self.plot_all_td()
        elif sel == 1:
            self.plot_all_bode()
            

    def on_update_plot(self, event):
        print('in on_update_plot')
        sel = self.td_bode_notebook.GetSelection()
        print('sel = %s' % sel)
        #pdb.set_trace()
        if sel == 0:
            #time domain plot
            labels = self.parse_label_str()
            self.cur_plot_description.plot_labels = labels
            legend_dict = self.parse_legend_str()
            self.cur_plot_description.legend_dict = legend_dict
            legloc = int(self.legloc_ctrl.GetValue())
            self.cur_plot_description.legloc = legloc
            #self.plot_cur_df()
            self.plot_all_td()
        elif sel == 1:
            #Bode plot
            input_str = self.bode_input_ctrl.GetValue()
            output_str = self.bode_output_ctrl.GetValue()
            self.cur_plot_description.bode_input_str = input_str
            self.cur_plot_description.bode_output_str = output_str
            #self.plot_cur_bode()
            self.plot_all_bode()


    def get_new_name(self):
        all_items = self.plot_name_list_box.GetItems()
        N_items = len(all_items)
        Q = N_items + 1
        new_name = 'plot_%i' % Q
        return new_name
        

    def get_pd_name(self, pd):
        """This is kind of a band-aid method to make up for the fact
        that I initially allowed plot_description instances without
        names.  I regret that and am sort of fixing it.

        Note that this method """
        name = pd.name
        if (not name) or (name == 'None'):
            name = self.get_new_name()
            pd.name = name
        return name


    def add_plot_description(self, pd):
        """This method consolidates everything needed to a plot
        description to the GUI.  The intent is to use it when loading
        plot descriptions from xml files or when the GUI user loads a
        data file."""
        #steps:
        # - update the GUI
        #   - plot speicific things#<-- only if it is the selected one
        #   - the plot_list
        # - add the pd to self.plot_dict
        # - add the name to self.plot_list
        all_items = self.plot_name_list_box.GetItems()
        name = self.get_pd_name(pd)
        print('all_items = ' + str(all_items))
        if name not in all_items:
            self.add_name_to_list_box(name)
            self.add_plot_description_to_backend(pd)
        

    def add_name_to_list_box(self, plot_name):
        self.plot_name_list_box.Append(plot_name)
        all_items = self.plot_name_list_box.GetItems()
        N_items = len(all_items)
        self.plot_name_list_box.Select(N_items-1)


    def add_plot_description_to_backend(self, plot_desc):
        name = self.get_pd_name(plot_desc)
        self.plot_dict[name] = plot_desc
        self.plot_list.append(name)

        
    def on_add_to_list_button(self, event):
        #FYI, this button no longer exists, but I still need the
        #method
        print('on_add_to_list_button')
        plot_name = self.plot_name_ctrl.GetValue()
        if plot_name:
            self.plot_name_list_box.Append(plot_name)
            all_items = self.plot_name_list_box.GetItems()
            N_items = len(all_items)
            self.plot_name_list_box.Select(N_items-1)
            self.plot_dict[plot_name] = self.cur_plot_description
            self.plot_list.append(plot_name)


    def set_figure_menu_text(self, fig_name, fig_num):
        ind = fig_num - 1
        text = 'Figure %i: %s' % (fig_num, fig_name)
        self.figure_menu_items[ind].SetText(text)


    def on_set_as_fig_button(self, event):
        dlg = figure_dialog(self.frame)
        if dlg.ShowModal() == wx.ID_OK:
            fig_name = dlg.figure_name_ctrl.GetValue()
            fig_num = int(dlg.figure_number_ctrl.GetValue())
            dlg.Destroy()
        else:
            dlg.Destroy()
            return
        
        
        inds = self.get_selected_plot_inds()
        pd_list = []
        for ind in inds:
            key = self.plot_name_list_box.GetString(ind)
            pd = self.plot_dict[key]
            pd_list.append(pd)

        sel = self.td_bode_notebook.GetSelection()
        if sel == 0:
            myclass = time_domain_figure
        elif sel == 1:
            myclass = bode_figure
        fig = myclass(fig_name, pd_list)
        self.active_fig = fig
        
        if fig_num > 9:
            print('only figure numbers up to 9 are supported')
            return

        if fig_num >= len(self.figure_list):
            empty_spots = fig_num - len(self.figure_list)
            self.figure_list += [None] * empty_spots

        ind = fig_num-1
        self.figure_list[ind] = fig
        self.set_figure_menu_text(fig_name, fig_num)
        ## text = 'Figure %i: %s' % (fig_num, fig_name)
        ## self.figure_menu_items[ind].SetText(text)

        
    def on_add_file(self, event):
        """
        Create and show the Open FileDialog
        """
        #print('in on_add_file')
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
            all_items = self.plot_name_list_box.GetItems()
            N_items = len(all_items)
            Q = N_items + 1
            start_name = 'plot_%i' % Q
            self.load_data_file(self.datapath, start_name)
            self.preview_grid.Refresh()
            self.plot_name_ctrl.SetValue(start_name)
            self.on_add_to_list_button(event)
            self.plot_all_td()
        dlg.Destroy()

        
        return filename, dirname


    def on_exit(self,event):
        self.frame.Close(True)  # Close the frame.    


    def on_change_plot_name(self, event):
        #inds = self.plot_name_list_box.GetSelections()
        #ind = inds[0]
        #key = self.plot_name_list_box.GetString(ind)
        items = self.plot_name_list_box.GetItems()
        key = self.old_name
        if key in items:
            ind = items.index(key)
            plot_ind = self.plot_list.index(key)
            val = self.plot_dict.pop(key)
            new_key = self.plot_name_ctrl.GetValue()
            val.name = new_key
            self.plot_list[plot_ind] = new_key
            self.plot_dict[new_key] = val
            self.plot_name_list_box.SetString(ind, new_key)


    def on_plot_name_get_focus(self, event):
        self.old_name = self.plot_name_ctrl.GetValue()


    def plot_parameters_to_gui(self, plot_description):
        label_str = plot_description.create_lable_str()
        self.label_text_ctrl.SetValue(label_str)
        legend_str = plot_description.create_legend_str()
        self.legend_dict_ctrl.SetValue(legend_str)
        if plot_description.bode_input_str is None:
            self.bode_input_ctrl.SetValue('')
        else:
            self.bode_input_ctrl.SetValue(plot_description.bode_input_str)
        if plot_description.bode_output_str is None:
            self.bode_output_ctrl.SetValue('')
        else:
            self.bode_output_ctrl.SetValue(plot_description.bode_output_str)
        folder, filename = os.path.split(plot_description.datapath)
        self.folder_ctrl.SetValue(folder)
        self.file_name_ctrl.SetValue(filename)
        plot_name = self.get_pd_name(plot_description)
        self.plot_name_ctrl.SetValue(plot_name)

        
        
    def on_plot_list_box_select(self, event):
        inds = self.plot_name_list_box.GetSelections()
        #pdb.set_trace()
        if len(inds) == 1:
            ind = inds[0]
            key = self.plot_name_list_box.GetString(ind)
            pd = self.plot_dict[key]
            self.plot_name_ctrl.SetValue(key)
            self.plot_parameters_to_gui(pd)
            self.cur_plot_description = pd
            

    def on_duplicate_button(self, event):
        print('in on_duplicate_button')
        key = self.plot_name_ctrl.GetValue()
        pd = self.plot_dict[key]
        new_pd = copy.copy(pd)
        new_key = key + '_copy'
        self.cur_plot_description = new_pd
        self.plot_name_ctrl.SetValue(new_key)
        self.on_add_to_list_button(event)


    def on_save_current_pd(self, event):
        print('in on_save_current_pd')

        dlg = wx.FileDialog(self.frame, message="Save Plot Description as XML",
                    defaultFile="",
                    wildcard=xml_wildcard,
                    style=wx.SAVE | wx.CHANGE_DIR
                    )

        if dlg.ShowModal() == wx.ID_OK:
            root = ET.Element('plot_description_file')
            self.cur_plot_description.create_xml(root)
            pretty_str = prettify(root)
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            filepath = os.path.join(dirname, filename)
            f = open(filepath, 'wb')
            f.write(pretty_str)
            f.close()

        dlg.Destroy()



    def on_save_figure(self, event):
        print('in on_save_figure')
        if not hasattr(self, 'active_fig'):
            print('no active_fig, leaving')
            #warn here? warning dialog?
            return
        elif self.active_fig is None:
            #warn here as well?
            #(I don't think this is actually possible -
            # self.active_fig doesn't have a default value)
            print('active_fig is None, leaving')
            return

        
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           msg="Save Figure as", \
                                           kind="save", \
                                           wildcard=xml_wildcard, \
                                           )
        if xml_path:
            root = ET.Element('figure')
            self.active_fig.create_xml(root)
            xml_utils.write_pretty_xml(root, xml_path)


    def on_save_gui_state(self, event):
        print('in on_save_gui_state')
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           msg="Save GUI state as", \
                                           kind="save", \
                                           wildcard=xml_wildcard, \
                                           )
        if xml_path:
            root = ET.Element('data_vis_gui_state')
            pd_list_xml = ET.SubElement(root, 'plot_description_list')

            for key in self.plot_list:
                pd = self.plot_dict[key]
                pd.create_xml(pd_list_xml)


            #figures
            first = 1
            for fig in self.figure_list:
                if fig is not None:
                    if first:
                        first = 0
                        fig_list_xml = ET.SubElement(root, 'figures')
                    fig.create_xml(fig_list_xml)
                    
                            
            inds = self.plot_name_list_box.GetSelections()
            params_xml = ET.SubElement(root, 'gui_params')
            plot_name = self.plot_name_ctrl.GetValue().encode()
            inds_str = str(list(inds))
            sel = self.td_bode_notebook.GetSelection()
            if sel == 0:
                plot_type = 'time_domain'
            elif sel == 1:
                plot_type = 'bode'

            
            af_name = 'None'
            if hasattr(self, 'active_fig'):
                if self.active_fig is not None:
                    af_name = self.active_fig.name
            
            mydict = {'selected_inds':inds_str, \
                      'active_plot_name':plot_name, \
                      'plot_type':plot_type, \
                      'active_fig':af_name}
                    
            xml_utils.append_dict_to_xml(params_xml, mydict)
            
            xml_utils.write_pretty_xml(root, xml_path)


    def on_load_gui_state(self, event):
        print('in on_load_gui_state')
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           msg="Load GUI state from XML", \
                                           kind="open", \
                                           wildcard=xml_wildcard, \
                                           )
        if xml_path:
            print('xml_path = ' + xml_path)
            myparser = gui_state_parser(xml_path)
            #pdb.set_trace()
            myparser.parse()
            myparser.convert()
            for pd in myparser.pd_list:
                self.add_plot_description(pd)


            #set the selected plots
            self.plot_name_list_box.DeselectAll()
            for ind in myparser.params['selected_inds']:
                self.plot_name_list_box.Select(ind)
            

            #set the current/active plot
            active_name = myparser.params['active_plot_name']
            active_pd = self.plot_dict[active_name]
            self.cur_plot_description = active_pd
            self.plot_parameters_to_gui(active_pd)


            # load figures here
            
            # it should be true that all the plot descriptions are
            # already loaded
            if myparser.has_figs:
                for fig in myparser.fig_list:
                    ind = self.find_empty_figure()
                    fig_num = ind + 1
                    self.set_figure_menu_text(fig.name, fig_num)
                    self.figure_list[ind] = fig

                if myparser.params.has_key('active_fig'):
                    active_fig_name = myparser.params['active_fig']
                    ind = self.find_fig_ind(active_fig_name)

                #ind will be the last ind aded if active_fig is not a
                #saved parameter
                self.set_active_figure(ind)

            self._update_plot()


    def find_empty_figure(self):
        #if there is a spot in self.figure_list that contains None,
        #find the first one of those.  If there aren't any, append
        #None and return the ind of the new None
        found_one = False
        for i, item in enumerate(self.figure_list):
            if item is None:
                found_one = True
                break

        if found_one:
            return i
        else:
            i = len(self.figure_list)
            self.figure_list.append(None)
            return i

        
    def on_load_figure(self, event):
        #What does it mean to load a Figure?
        # - add the plot descriptions (if they are not already there)
        # - add figure name to the figure menu
        # - add figure instance to fig_list
        # - set the active figure
        #   - select the right plot descriptions
        # - redraw the figure
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                   msg="Chose an XML file", \
                                   default_file="", \
                                   wildcard=xml_wildcard)
        if xml_path:
            myparser = figure_parser(xml_path)
            myparser.parse()
            myfig = myparser.convert()
            for pd in myfig.plot_descriptions:
                self.add_plot_description(pd)
            #set active plot_description
            self.cur_plot_description = pd
            self.plot_parameters_to_gui(pd)
            
            ind = self.find_empty_figure()
            fig_num = ind + 1
            self.set_figure_menu_text(myfig.name, fig_num)
            self.figure_list[ind] = myfig
            self.set_active_figure(ind)

        
    def set_current_plot_descrition(self, pd):
        self.plot_parameters_to_gui(pd)
        self.cur_plot_description = pd
        
        
    def on_load_plot_descriptions(self, event):
        print('in on_load_plot_descriptions')
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           msg="Chose an XML file", \
                                           default_file="", \
                                           wildcard=xml_wildcard)
        if xml_path:
            myparser = plot_description_file_parser(xml_path)
            myparser.parse()
            pd_list = myparser.convert()

            for pd in pd_list:
                self.add_plot_description(pd)

            self.set_current_plot_descrition(pd_list[-1])
            self._update_plot()

            


        
    def OnInit(self):
        #xrcfile = cbook.get_sample_data('ryans_first_xrc.xrc', asfileobj=False)
        xrcfile = 'data_vis_xrc.xrc'
        #xrcfile = 'data_vis_xrc_broken.xrc'
        #xrcfile = 'data_vis_xrc_editted.xrc'
        print('loading', xrcfile)

        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        ## self.panel = xrc.XRCCTRL(self.frame,"MainPanel")
        ## self.new_element_choice = xrc.XRCCTRL(self.frame, "new_element_choice")
        ## self.new_element_choice.SetItems(sorted_elements)
        self.td_bode_notebook = xrc.XRCCTRL(self.frame,"td_bode_notebook")
        self.bode_input_ctrl = xrc.XRCCTRL(self.frame,"bode_input_ctrl")
        self.bode_output_ctrl = xrc.XRCCTRL(self.frame,"bode_output_ctrl")
        self.add_file_button = xrc.XRCCTRL(self.frame,"add_file")
        self.update_plot_button = xrc.XRCCTRL(self.frame, "update_plot_button")
        self.folder_ctrl = xrc.XRCCTRL(self.frame, "folder_ctrl")
        self.file_name_ctrl = xrc.XRCCTRL(self.frame, "file_name_ctrl")
        self.plot_name_ctrl = xrc.XRCCTRL(self.frame, "plot_name_ctrl")
        self.set_as_fig_button = xrc.XRCCTRL(self.frame, "set_as_fig_button")
        self.remove_button = xrc.XRCCTRL(self.frame, "remove_button")
        self.duplicate_button = xrc.XRCCTRL(self.frame, "duplicate_button")
        self.plot_name_list_box = xrc.XRCCTRL(self.frame, "plot_name_list_box")
        self.plot_name_list_box.Bind(wx.EVT_LISTBOX, self.on_plot_list_box_select)
        wx.EVT_BUTTON(self.add_file_button, self.add_file_button.GetId(),
                      self.on_add_file)
        wx.EVT_BUTTON(self.update_plot_button, self.update_plot_button.GetId(),
                      self.on_update_plot)
        wx.EVT_BUTTON(self.set_as_fig_button, self.set_as_fig_button.GetId(), \
                      self.on_set_as_fig_button)
        wx.EVT_BUTTON(self.duplicate_button, self.duplicate_button.GetId(), \
                      self.on_duplicate_button)
        self.label_text_ctrl = xrc.XRCCTRL(self.frame, "label_text_ctrl")
        self.legend_dict_ctrl = xrc.XRCCTRL(self.frame, "legend_dict_ctrl")
        self.legloc_ctrl = xrc.XRCCTRL(self.frame, "legloc_ctrl")
        self.legloc_ctrl.SetValue("1")
        #pdb.set_trace()
        self.menubar = self.frame.GetMenuBar()
        self.frame.Bind(wx.EVT_MENU, self.on_add_file, \
                        id=xrc.XRCID('add_file_menu'))
        self.frame.Bind(wx.EVT_MENU, self.on_update_plot, \
                        id=xrc.XRCID('update_plot_menu'))
        self.frame.Bind(wx.EVT_MENU, self.on_exit, \
                        id=xrc.XRCID('exit_menu'))
        self.frame.Bind(wx.EVT_MENU, self.on_save_current_pd, \
                        id=xrc.XRCID('save_plot_description'))
        self.frame.Bind(wx.EVT_MENU, self.on_save_gui_state, \
                        id=xrc.XRCID('save_gui_state'))
        self.frame.Bind(wx.EVT_MENU, self.on_save_figure, \
                        id=xrc.XRCID('save_figure'))
        self.frame.Bind(wx.EVT_MENU, self.on_load_plot_descriptions, \
                        id=xrc.XRCID('load_plot_descriptions'))
        self.frame.Bind(wx.EVT_MENU, self.on_load_gui_state, \
                        id=xrc.XRCID('load_gui_state'))
        self.frame.Bind(wx.EVT_MENU, self.on_load_figure, \
                        id=xrc.XRCID('load_figure'))
        self.frame.Bind(wx.EVT_MENU, self.on_switch_to_bode, \
                        id=xrc.XRCID('switch_to_bode'))
        self.frame.Bind(wx.EVT_MENU, self.on_switch_to_time_domain, \
                        id=xrc.XRCID('switch_to_time_domain'))
        
        self.plot_name_ctrl.Bind(wx.EVT_KILL_FOCUS, self.on_change_plot_name)
        self.plot_name_ctrl.Bind(wx.EVT_SET_FOCUS, self.on_plot_name_get_focus)
        self.plot_name_ctrl.Bind(wx.EVT_TEXT_ENTER, self.on_change_plot_name)
        #create figure menu with associated hot key accelerators
        figure_menu = wx.Menu()
        figure_menu_ids = []
        figure_menu_items = []

        accelEntries = []


        cur_id = wx.NewId()
        cur_text = 'Set as Figure'
        help_text = 'Set currently selected plots to a Figure #'
        cur_item = wx.MenuItem(figure_menu, cur_id, cur_text, help_text)
        figure_menu.AppendItem(cur_item)
        accelEntries.append((wx.ACCEL_CTRL, ord('F'), cur_id))
        #method_name = 'plot_fig_%i' % j
        self.Bind(wx.EVT_MENU, self.on_set_as_fig_button, id=cur_id)


        for i in range(9):
            j = i+1
            cur_id = wx.NewId()
            cur_text = 'Figure %i' % j
            help_text = 'Plot Figure %i' % j
            cur_item = wx.MenuItem(figure_menu, cur_id, cur_text, help_text, \
                                   wx.ITEM_RADIO)
            figure_menu.AppendItem(cur_item)
            figure_menu_ids.append(cur_id)
            figure_menu_items.append(cur_item)

            accelEntries.append((wx.ACCEL_CTRL, ord('%i' % j), cur_id))
            #method_name = 'plot_fig_%i' % j
            self.Bind(wx.EVT_MENU, self.change_fig, id=cur_id)

        self.figure_menu_ids = figure_menu_ids
        self.figure_menu = figure_menu
        self.menubar.Append(self.figure_menu, "Figures")
        self.figure_menu_items = figure_menu_items

        accelTable  = wx.AcceleratorTable(accelEntries)
        self.frame.SetAcceleratorTable(accelTable)

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
        self.plot_dict = {}
        self.plot_list = []
        self.figure_list = []
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




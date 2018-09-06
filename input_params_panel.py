from __future__ import print_function

import sys, time, os, gc, rwkos

import wx
import wx.xrc as xrc

import wx.grid
#import wx.grid as  gridlib

#import xml.etree.ElementTree as ET
#from xml.dom import minidom

from panel_with_params_grid import panel_with_params_grid

import block_diagram_xml
import xml_utils

import pdb

xrc_folder = rwkos.FindFullPath('git/wxpython_guis')
filename = 'input_params_xrc.xrc'
xrc_path = os.path.join(xrc_folder, filename)


input_dict = {'finite_width_pulse':['t_on','t_off','amp'], \
              'step_input':['t_on','amp'], \
              'swept_sine':['fmin','fmax','deadtime','amp'], \
              }

common_params = ['max_T']#<---- should swept_sine have a max_T rather than tspan? (just get rid of tspan?)
defaults_dict = {'max_T':2.0, 't_on':0.1, 'amp':100}

for key, val in input_dict.items():
    val.extend(common_params)
    input_dict[key] = val#don't sure if this is necessary since val
                         #is a reference to a list


sorted_inputs = sorted(input_dict.keys())


def validate_dict(dict_in):
    all_good = True
    for key, val in dict_in.items():
        if (val is None) or (val == ''):
            all_good = False
            wx.MessageBox('Empty value for parameter %s' % key)

    return all_good
        
            
class input_params_panel(panel_with_params_grid):
    def _set_params(self, case='step_input'):
        key = case
        params_list = input_dict[key]
        N = len(params_list)
        defaults = [None]*N
        starting_dict = dict(zip(params_list, defaults))

        for key, val in defaults_dict.items():
            if starting_dict.has_key(key):
                starting_dict[key] = val
        
        #starting_dict.update(defaults_dict)
        self.display_params(starting_dict)

        
    def on_input_choice(self, event=0):
        print('in on_input_choice')
        key = self.input_choice.GetStringSelection()
        self._set_params(key)


    def get_input_params(self):
        case = self.input_choice.GetStringSelection()
        #pdb.set_trace()
        mydict = self.build_params_dict()
        for key, val in mydict.items():
            val = xml_utils.try_string_to_number(val)
            mydict[key] = val
            
        exit_status = validate_dict(mydict)
        if not exit_status:
            return case, None
        else:
            return case, mydict
    
        
    def __init__(self, parent):
        pre = wx.PrePanel()
        res = xrc.XmlResource(xrc_path)
        res.LoadOnPanel(pre, parent, "main_panel") 
        self.PostCreate(pre)
        self.parent = parent
        ## self.Bind(wx.EVT_BUTTON, self.on_update_diagram, \
        ##           xrc.XRCCTRL(self, "update_diagram_button")) 
        self.input_choice = xrc.XRCCTRL(self, "input_choice")
        self.input_choice.SetItems(sorted_inputs)
        wx.EVT_CHOICE(self.input_choice, self.input_choice.GetId(),
                      self.on_input_choice)

        self.params_grid = xrc.XRCCTRL(self, "params_grid")
        self.params_grid.CreateGrid(20,2)
        starting_case = 'step_input'
        index = sorted_inputs.index(starting_case)
        self.input_choice.Select(index)
        self._set_params(case=starting_case)
        

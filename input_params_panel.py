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

xrc_folder = rwkos.FindFullPath('git/wxpython_guis')
filename = 'input_params_xrc.xrc'
xrc_path = os.path.join(xrc_folder, filename)


input_dict = {'arbitrary_input':[], \
              'finite_width_pulse':['t_on','t_off','amp'], \
              'step_input':['t_on','amp'], \
              'swept_sine':['fmin','fmax','tspan','deadtime','amp'], \
              }

common_params = ['max_T']

for key, val in input_dict.iteritems():
    val.extend(common_params)
    input_dict[key] = val#don't sure if this is necessary since val
                         #is a reference to a list


sorted_inputs = sorted(input_dict.iterkeys())


class input_params_panel(panel_with_params_grid):
    def on_input_choice(self, event=0):
        print('in on_input_choice')
        key = 

        
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

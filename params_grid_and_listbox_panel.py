"""This module contains a panel that creates tikz block diagrams from
an xml description of a system.  These block diagrams are converted to
jpegs and placed on a static bitmap.

Note that I am using self.bd_parent.blocklist to prevent a toplevel
application from having multiple blocklists for each panel and having
them get out of sync."""

from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')

use_pdfviewer = False
max_rows = 20

import os, copy, rwkos

#import sys, time, os, gc

import wx
import wx.xrc as xrc

#import wx.grid
#import wx.grid as  gridlib
import numpy as np

import block_diagram_utils
from block_diagram_utils import panel_with_parent_blocklist, change_ext

from panel_with_params_grid import panel_with_params_grid

import xml_utils

#xrc_folder = '/Users/rkrauss/git/wxpython_guis/'
xrc_folder = rwkos.FindFullPath('git/wxpython_guis')
xrc_path = os.path.join(xrc_folder, 'params_grid_and_listbox_panel_take2.xrc')

block_params = {'arbitrary_input':[], \
                'finite_width_pulse':['t_on','t_off','amp'], \
                'step_input':['t_on','amp'], \
                'TF_block':['num','den','input','c2dmethod'], \
                'DTTMM_block':['xmlpath','input'], \
                'zoh_block':['input'], \
                'summing_block':['input','input2'], \
                'swept_sine':['fmin','fmax','tspan','deadtime','amp'], \
                'serial_plant':['microcontroller','input','sensors','actuators'], \
                'gain_block':['gain','input'], \
                'saturation_block':['max','min','input'], \
                'digital_TF_block':['numz','denz','input'], \
                }

common_props = ['label','caption','position_type','show_outputs',\
                'tikz_block_options','input_ind']
output_opts = ['show_output_arrows','output_distances','output_angles','output_labels']

required_opts = common_props

for key, val in block_params.iteritems():
    val.extend(common_props)
    block_params[key] = val#don't sure if this is necessary since val
        #is a reference to a list

relative_props = ['relative_block','relative_direction','relative_distance', 'xshift', 'yshift']
abs_props = ['abs_coordinates']

#options to copy when a block is replaced
copy_opts = ['input'] + common_props + output_opts + relative_props + abs_props

tikz_opts = ['position_type','show_outputs','tikz_block_options'] + \
            output_opts + relative_props + abs_props

sorted_blocks = sorted(block_params.iterkeys())


class params_grid_and_listbox_panel(panel_with_params_grid, \
                                    wx.Panel, \
                                    panel_with_parent_blocklist):
    ## def set_param_labels(self):
    ##     self.clear_params_grid()
    ##     key = self.get_new_block_type()
    ##     cur_params = block_params[key]
    ##     for i, item in enumerate(cur_params):
    ##         if item is None:
    ##             item = ''
    ##         self.params_grid.SetCellValue(i+1,0, item)


    def on_popup_item_selected(self, event):
        item = self.popupmenu.FindItemById(event.GetId())
        text = item.GetText()
        #wx.MessageBox("You selected item '%s'" % text)
        self.popup_choice = text


    def create_popup_menu(self, item_list):
        self.popupmenu = wx.Menu()
        self.popup_choice = None

        for item in item_list:
            menu_item = self.popupmenu.Append(-1, item)
            self.Bind(wx.EVT_MENU, self.on_popup_item_selected, menu_item)




    def on_show_outputs_change(self):
        print('in on_show_outputs_change')
        show_outs_str = self.get_grid_val('show_outputs')
        show_outs_bool = xml_utils.str_to_bool(show_outs_str)
        if show_outs_bool:
            self.append_rows_if_missing(output_opts)
            #try to determine sensible defaults
            #
            # ? how do I determine info about the active block?
            #
            # output_opts = ['show_output_arrows','output_distances','output_angles']
            output_str = self.get_grid_val('sensors')
            show_arrows = [True]
            out_distances = [1.0]
            out_angles = [0]
            out_labels = ['']

            if output_str:
                my_outputs = xml_utils.full_clean(output_str)
                if type(my_outputs) == list:
                    num_out = len(my_outputs)
                    show_arrows = [True]*num_out
                    out_distances = [1.0]*num_out
                    out_labels = ['']*num_out
                    if num_out == 1:
                        out_angles = [0]
                    elif num_out == 2:
                        out_angles = [-30,30]
                    elif num_out == 3:
                        out_angles = [-45,0,45]
                    elif num_out == 4:
                        out_angles =[-45, -15, 15, 45]

            self.set_grid_val('output_angles', out_angles)
            self.set_grid_val('output_distances', out_distances)
            self.set_grid_val('show_output_arrows', show_arrows)
            self.set_grid_val('output_labels', out_labels)
        else:
            self.delete_grid_rows(output_opts)



    def on_position_type_change(self, old_val):
        print('in on_position_type_change')
        i = 0
        pos_type = self.get_grid_val('position_type')
        if pos_type == 'absolute':
            del_props = relative_props
            new_props = abs_props
        elif pos_type == 'relative':
            del_props = abs_props
            new_props = relative_props
        print('before delete_grid_rows')
        if pos_type != old_val:
            self.delete_grid_rows(del_props)
        print('after delete_grid_rows')
        self.append_rows_if_missing(new_props)
        print('after append_rows')
        self.autosize_columns()


    def _get_other_blocks(self):
        """Get a list of blocks from the list box that does not
        include the currently selected block.  This is slightly tricky
        because the block whose parameters are being editted may not
        be in the list box yet if it hasn't been added yet"""
        index = self.block_list_box.GetSelection()
        all_blocks = self.block_list_box.GetItems()#this will start out with all the blocks
        #don't pop if the current block isn't actually in the list yet
        other_blocks = copy.copy(all_blocks)
        curname = self.new_block_name_box.GetValue()
        selected_name = self.block_list_box.GetStringSelection()
        if curname==selected_name:
            selected_block = other_blocks.pop(index)
        print('other_blocks = ' + str(other_blocks))
        return other_blocks


    def create_true_false_popup_menu(self):
        self.create_popup_menu(['True','False'])


    def set_xmlpath_from_dialog(self):
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           msg="Load DT-TMM system from XML", \
                                           kind="open", \
                                           wildcard=xml_wildcard, \
                                           )
        if xml_path:
            self.set_grid_val('xmlpath', xml_path)


    def show_popup_menu(self, event):
        print('in show_popup_menu')
        ## old way that works with other event types:
        ## x, y = self.params_grid.CalcUnscrolledPosition(event.GetX(), \
        ##                                                event.GetY())
        ## coords = self.params_grid.XYToCell(x, y)
        ## col = coords[1]
        ## row = coords[0]
        col = event.GetCol()
        row = event.GetRow()
        print('col = %s' % col)
        print('row = %s' % row)
        attr = self.params_grid.GetCellValue(row,0)
        attr = attr.strip()
        old_val = self.params_grid.GetCellValue(row,1)
        old_val = old_val.strip()
        print('attr=%s' % attr)
        if attr in ['input', 'relative_block', 'input2']:
            other_blocks = self._get_other_blocks()
            self.create_popup_menu(other_blocks)
        elif attr == 'position_type':
            self.create_popup_menu(['absolute','relative'])
        elif attr == 'microcontroller':
            self.create_popup_menu(['arduino','psoc'])
        elif attr == 'relative_direction':
            self.create_popup_menu(['right of','left of','below of','above of'])
        elif attr == 'show_outputs':
            self.create_true_false_popup_menu()
        elif attr == 'c2dmethod':
            self.create_popup_menu(['tustin','zoh'])
        elif attr == 'xmlpath':
            #we aren't going to actually do a popup menu, so this is
            #slightly tricky
            self.set_xmlpath_from_dialog()
            return
        else:
            print('no popup menu for attribute %s' % attr)
            return

        #actually show the popup menu
        #pos = event.GetPosition()
        #pos = self.frame.ScreenToClient(pos)
        result = self.frame.PopupMenu(self.popupmenu)#, pos)
        print('result = %s' % result)
        if result and hasattr(self, 'popup_choice'):
            if self.popup_choice:
                self.params_grid.SetCellValue(row, col, self.popup_choice)

            self.on_cell_change()
            #post-processing
            if attr == 'position_type':
                self.on_position_type_change(old_val)

            elif attr == 'show_outputs':
                self.on_show_outputs_change()


    def display_params(self, elem, filt_func=None, \
                       my_required_opts=required_opts):
        params_dict = elem.params
        self.clear_params_grid()
        keys = params_dict.keys()
        keys.sort()
        if filt_func is None:
            filt_keys = keys
        else:
            filt_keys = filter(filt_func, keys)
            print('keys = ' + str(keys))
            print('filt_keys = ' + str(filt_keys))
            
        for i, key in enumerate(filt_keys):
            self.params_grid.SetCellValue(i+1,0, key)
            val = params_dict[key]
            if val is None:
                val = ''
            if type(val) not in [str, unicode]:
                val = str(val)
            self.params_grid.SetCellValue(i+1,1, val)

        self.append_rows_if_missing(my_required_opts)


    def on_cell_change(self, event=None):
        index = self.block_list_box.GetSelection()
        #block_name = self.new_block_name_box.GetValue()
        # ^-- this is a problem since we don't have this text box
        #     thinking about this will be a key to modularity between this panel and
        #     my non-modular block_diagram_gui.py
        #
        #     Design decision: the problem here is that the non-modular existing code
        #     has a notion of a new block that isn't really in self.blocklist yet.
        #     This makes a mess.  The right answer is to have a dialog that pops up
        #     when adding a new block.  If the user closes that dialog with OK, the block
        #     will be added.  The dialog will need to share all the right-clicking code
        #     with this panel.  That could get slightly messy with blocklist, but
        #     since the dialog won't be allowed to edit the blocklist, I think it will be
        #     ok.
        params_dict = self.build_params_dict()
        self.bd_parent.blocklist[index].params.update(params_dict)#<-- updating rather than overwriting/assigning
                                                               #    will help if some parameters are hidden
                                                               #    (i.e. not showing the tikz params or something)
            
        #self.params_grid.AutoSizeColumns()
        
        
    def on_block_select(self, event):
        print('in on_block_select')
        curname = self.block_list_box.GetStringSelection()
        index = self.block_list_box.GetSelection()
        print('curname = %s, index = %i' % (curname, index))
        elem = self.bd_parent.blocklist[index]
        #self.new_block_name_box.SetValue(elem.name)#<-- if you wanted to be able to edit the name of a block, what would you do?
        #                                                 - what about just putting block name as the first parameter
        #                                                    - it could be just a little bit of hassle to handle this well
        self.display_params(elem)
        self.autosize_columns()

        

    def sort_list_box(self):
        for i, block in enumerate(self.bd_parent.blocklist):
            self.block_list_box.SetString(i, block.name)


    def reset_list_box(self):
         self.block_list_box.Clear()

         for block in self.bd_parent.blocklist:
             self.block_list_box.Append(block.name)
             
  
    def __init__(self, parent, bd_parent):
        pre = wx.PrePanel()
        res = xrc.XmlResource(xrc_path)
        res.LoadOnPanel(pre, parent, "params_grid_panel") 
        self.PostCreate(pre)
        self.parent = parent
        self.bd_parent = bd_parent
        assert hasattr(self.bd_parent, 'blocklist'), \
               "The parent of a tikz_viewer_panel must have a blocklist attribute."

        self.params_grid = xrc.XRCCTRL(self,"params_grid")
        self.block_list_box = xrc.XRCCTRL(self, "block_list_box")

        wx.EVT_LISTBOX(self.block_list_box, self.block_list_box.GetId(),
                       self.on_block_select)

        self.params_grid.CreateGrid(max_rows,2)
        self.clear_params_grid()

        self.params_grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK,
                      self.show_popup_menu)
        self.params_grid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, \
                              self.on_cell_change)





def filt_tikz(item):
    return bool(item not in tikz_opts)


required_opts2 = filter(filt_tikz, required_opts)


class params_grid_panel_hide_tikz(params_grid_and_listbox_panel):
    def display_params(self, elem):
        params_grid_and_listbox_panel.display_params(self, \
                                                     elem, \
                                                     filt_func=filt_tikz, \
                                                     my_required_opts=required_opts2)

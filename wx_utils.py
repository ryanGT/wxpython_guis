import os

import wx
import wx.xrc as xrc

import wx.grid

import xml.etree.ElementTree as ET
import xml_utils

def my_dir_dialog(parent=None,\
                  start_dir="",\
                  msg="Choose a directory", \
                  style=wx.DD_DEFAULT_STYLE,
                  ):

    dlg = wx.DirDialog(parent, msg, \
                        start_dir,
                        style)

    if dlg.ShowModal() == wx.ID_OK:
        pathout = dlg.GetPath()
    else:
        pathout = None

    dlg.Destroy()

    return pathout



    
def my_file_dialog(parent=None, \
                   msg="Chose a file", default_file="", \
                   start_dir="", \
                   wildcard="All files (*.*)|*.*", \
                   kind="open", \
                   check_overwrite=False):
    """This is a convienence class for showing a file dialog for
    opening or saving a file.  kind can be either 'open' or 'save'.

    If the user clicks OK, the full filepath is returned.  If the user
    cancels the dialog, None is returned."""
    flags = wx.CHANGE_DIR
    
    if kind.lower() in ["open","load"]:
        flags |= wx.OPEN
    elif kind.lower() == "save":
        flags |= wx.SAVE
        if check_overwrite:
            flags |= wx.OVERWRITE_PROMPT
            
        
    dlg = wx.FileDialog(parent, message=msg, \
                        defaultFile=default_file, \
                        defaultDir=start_dir, \
                        wildcard=wildcard, \
                        style=flags, \
                        )
    
    if dlg.ShowModal() == wx.ID_OK:
        filename = dlg.GetFilename()
        dirname = dlg.GetDirectory()
        filepath = os.path.join(dirname, filename)
    else:
        filepath = None

    dlg.Destroy()

    return filepath


class gui_that_saves(object):
    """A mixin class for saving to xml based on calling the GetValue
    method for a list of wxPython controls."""
    def create_xml(self, root_name, control_attr_list):
        """generate xml for saving the gui state.  control_attr_list
        is a list of strings containing the names of the gui attrs
        whose GetValue methods should be called"""
        xml_root = root = ET.Element(root_name)

        for attr in control_attr_list:
            control = getattr(self, attr)
            if hasattr(control, 'GetValue'):
                value = control.GetValue()
            elif hasattr(control, 'GetSelection'):
                value = str(control.GetSelection())
            ## if value.find('Ryan') > -1:
            ##     import pdb
            ##     pdb.set_trace()
            cur_xml = ET.SubElement(xml_root, attr)
            cur_xml.text = value#.encode('UTF-8')

        self.xml = xml_root


    def load_xml(self, filename):
        parser = xml_utils.xml_parser(filename)
        mydict = xml_utils.children_to_dict(parser.root)
        for attr, val in mydict.iteritems():
            control = getattr(self, attr)
            if hasattr(control, 'SetValue'):
                if val is None:
                    val = u''
                control.SetValue(val)
            elif hasattr(control, 'SetSelection'):
                control.SetSelection(int(val))
            

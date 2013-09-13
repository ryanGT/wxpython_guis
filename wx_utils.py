import os

import wx
import wx.xrc as xrc

import wx.grid

def my_file_dialog(parent=None, \
                   msg="Chose a file", default_file="", \
                   wildcard="All files (*.*)|*.*", \
                   kind="open", \
                   check_overwrite=True):

    flags = wx.CHANGE_DIR
    
    if kind.lower() in ["open","load"]:
        flags |= wx.OPEN
    elif kind.lower() == "save":
        flags |= wx.SAVE
        if check_overwrite:
            flags |= wx.OVERWRITE_PROMPT
            
        
    dlg = wx.FileDialog(parent, message=msg, \
                        defaultFile=default_file, \
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

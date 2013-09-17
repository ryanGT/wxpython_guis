import os

import wx
import wx.xrc as xrc

import wx.grid

def my_file_dialog(parent=None, \
                   msg="Chose a file", default_file="", \
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

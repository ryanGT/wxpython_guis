#!/usr/bin/env python
#from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')


"""This gui exists to map one column from a spreadsheet of individual
students (not teams) to another spreadsheet of individual student
data.  This was initially used to append emails from a detailed student
list from banner to a bb_download spreadsheet from blackboard to form all
of the needed columns for catme."""

#-------------------------
#
# To Do:
#
# - allow multiple columns to be mapped
# - allow xls or ods team grade files instead of just csv
# - have a file dialog to allow final output csv to be renamed
# - save the previous values of all widgets
#
#-------------------------
import sys, time, os, gc, glob, shutil

import wx
import wx.xrc as xrc

import wx.grid

import wx_utils, relpath, rst_creator, rwkos, txt_mixin, txt_database, datetime
import xml_utils
from xml_utils import prettify
#import ind_grade_mapper
import spreadsheet_mapper

xml_wildcard = "XML files (*.xml)|*.xml"

import re

import file_finder

import pdb

class MyApp(wx.App, wx_utils.gui_that_saves):
    def save(self, event=None):
        course = self.get_course()
        xml_name = 'course_prep_%s.xml' % course
        xml_path = os.path.join(git_dir, xml_name)
        ## xml_path = wx_utils.my_file_dialog(parent=self.frame, \
        ##                                    msg="Save GUI state as", \
        ##                                    kind="save", \
        ##                                    wildcard=xml_wildcard, \
        ##                                    )

        control_attr_list = ['coursechoice','lab_number_box','source_folder_box',\
                             'lab_title_box']
        self.create_xml('course_prep_gui', control_attr_list)
        
        print('xml_path = ' + xml_path)
        xml_utils.write_pretty_xml(self.xml, xml_path)


    def load(self, event=None):
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           start_dir=self.start_dir, \
                                           msg="Choose an xml file", \
                                           kind="open", \
                                           wildcard=xml_wildcard, \
                                           )
        self.load_xml(xml_path)


    ## def get_title(self):
    ##     title = self.lab_title_box.GetValue()
    ##     return title.encode()


    ## def set_lab_number(self):
    ##     course = self.get_course()
    ##     #print('course = %s' % course)
    ##     new_num = suggest_lab_number(course)
    ##     self.lab_number_box.SetValue(str(new_num))


    def show_help(self, event=None):
        msg = "This is gui was originally created to append " + \
              "email addresses to a spreadsheet containing names and team numbers " + \
              "for Catme.  Source Spreadsheet contains the column you want to append " + \
              "and Main Spreadsheet is the one that is being appended.\n\n" + \
              "Note: these are both individual spreadsheets, not team spreadsheets.\n\n" + \
              "The Go Catme option seeks to change the column labels to those expected by Catme:\n" + \
              "    first, last, email, id, and team."
        caption = "Help Dialog"
        dialog = wx.MessageDialog(self.frame, message=msg, caption=caption)
        dialog.ShowModal()
        dialog.Destroy()
        

    def make_rel(self, pathin):
        rp = relpath.relpath(pathin, self.root)
        return rp
    

    def make_abs(self, pathin):
        ap = os.path.join(self.root, pathin)
        return ap

    def path_to_box(self, mybox, mypath):
        mybox.SetValue(self.make_rel(mypath))


    def path_from_box(self, mybox):
        rp = mybox.GetValue()
        ap = self.make_abs(rp)
        return ap


    def _browse(self, save_box, msg):
        mypath = wx_utils.my_file_dialog(parent=None, \
                                         start_dir=self.start_dir, \
                                         msg=msg, \
                                         )
        if mypath:
            #rp = relpath.relpath(folder_path, base=course_dir)
            self.path_to_box(save_box, mypath)


    def get_source_labels(self):
        mypath = self.path_from_box(self.source_folder_box)
        if mypath:
            print("mypath = " + mypath)
            myfile = txt_mixin.delimited_txt_file(mypath)
            labels = myfile.array[0,:]
            return labels
        return None


    def update_grade_cols(self):
        print("in update_grade_cols")
        labels = self.get_source_labels()
        if labels is not None:
            self.source_listbox.Clear()
            self.source_listbox.Append(labels)
            

    def on_source_browse(self, event=None):
        msg = "Choose the team grades spreadsheet"
        self._browse(self.source_folder_box, msg)
        self.update_grade_cols()
        

    def on_main_browse(self, event=None):
        msg = "Choose the team list spreadsheet"
        self._browse(self.main_folder_box, msg)

        
        
    def my_init(self):
        print("hello");
        self.root = os.getcwd()
        team_csv_path = self.search_for_bb_teamlist()
        if team_csv_path is not None:
            self.path_to_box(self.main_folder_box,team_csv_path)
        self.start_dir = "."

        #self.set_lab_number()


    def find_team_label(self, csv_path):
        myfile = txt_mixin.delimited_txt_file(csv_path)
        labels = myfile.array[0,:]
        print("labels: " + str(labels))
        if labels is not None:
            pat = re.compile("[Tt]eam")
            matches = []
            for i, item in enumerate(labels):
                q = pat.search(item)
                if q:
                    matches.append(i)

            if len(matches) == 1:
                return(labels[matches[0]])
            else:
                return None


    def catme_go(self, event=None):
        print("in catme_go")
        self._go(catme=True)


    def go(self, event=None):
        self._go(catme=False)
        

    def _go(self, catme=False):
        print("going....")
        source_csv_path = self.path_from_box(self.source_folder_box)
        main_csv_path = self.path_from_box(self.main_folder_box)
        if not main_csv_path:
            # exit
            return None

        ind = self.source_listbox.GetSelection()
        if ind is None:
            #exit
            return None
        src_label = self.source_listbox.GetString(ind)
        mymapper = spreadsheet_mapper.delimited_grade_spreadsheet(main_csv_path)
        mymapper.map_from_path(source_csv_path, src_label)
        if catme:
            mymapper.catme_labels()
            
        # browse for output name
        outpath = wx_utils.my_file_dialog(parent=None, \
                                          start_dir=self.start_dir, \
                                          msg="Select output file", \
                                          wildcard="CSV files (*.csv)|*.csv", \
                                          kind="save", \
                                          )

        if outpath:
            mymapper.save(outpath)
            
        

    def OnActivate(self, evt):
        print("in OnActivate")


    def search_for_bb_teamlist(self, csv_pat="*bb*download*team*.csv"):
        """Search in the current directory and up the tree for
        '*bb*download*team*.csv'"""
        folder = os.getcwd()
        while folder != os.path.sep:
            files = glob.glob(os.path.join(folder,csv_pat))
            if files:
                return files[0]
            else:
                folder, other = os.path.split(folder)
                if not other:
                    return None
                
        
        
    def OnInit(self):
        """Initialize the :py:class:`MyApp` instance; start by loading
        the xrc resource file and then add other stuff and bind the events"""
        xrcfile = '/Users/kraussry/git/wxpython_guis/ind_spreadsheet_mapper_xrc.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"main_panel")

        self.source_folder_box = xrc.XRCCTRL(self.frame,"source_folder_box")
        self.source_browse = xrc.XRCCTRL(self.frame, "source_browse")
        self.main_browse = xrc.XRCCTRL(self.frame, "main_browse")
        self.main_folder_box = xrc.XRCCTRL(self.frame,"main_folder_box")
        self.source_listbox = xrc.XRCCTRL(self.frame,"list_box_1")
        self.go_button = xrc.XRCCTRL(self.frame, "go_button")
        self.go_catme_button = xrc.XRCCTRL(self.frame, \
                                           "go_catme_button")        
        #self.lab_title_box.SetFocus()
        
        wx.EVT_BUTTON(self.source_browse, self.source_browse.GetId(), \
                      self.on_source_browse)
        wx.EVT_BUTTON(self.main_browse, self.main_browse.GetId(), \
                      self.on_main_browse)
        wx.EVT_BUTTON(self.go_button, self.go_button.GetId(), \
                      self.go)
        wx.EVT_BUTTON(self.go_catme_button, self.go_catme_button.GetId(), \
                      self.catme_go)

        self.menubar = self.frame.GetMenuBar()
        ## self.frame.Bind(wx.EVT_MENU, self.on_exit, \
        ##                 id=xrc.XRCID('quit_menu_item'))

        self.frame.Bind(wx.EVT_MENU, self.go, \
                        id=xrc.XRCID('menu_go'))
        self.frame.Bind(wx.EVT_MENU, self.catme_go, \
                        id=xrc.XRCID('menu_catme_go'))
        self.frame.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        self.frame.Bind(wx.EVT_MENU, self.show_help, \
                        id=xrc.XRCID('menu_show_help'))
        # set up accelerators
        accelEntries = []
        accelEntries.append((wx.ACCEL_CTRL, ord('G'), xrc.XRCID("menu_go")))

        accelTable  = wx.AcceleratorTable(accelEntries)
        self.frame.SetAcceleratorTable(accelTable)


        ## self.frame.Bind(wx.EVT_MENU, self.load, \
        ##         id=xrc.XRCID('load_menu_item'))

        
        self.my_init()
        # Intial debugging
        #L4title = "Open-Loop DC Motor Control"
        #self.lab_title_box.SetValue(L4title)
        self.frame.SetClientSize((625,350))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()


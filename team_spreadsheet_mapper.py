#!/usr/bin/env python
#from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')

import sys, time, os, gc, glob, shutil

import wx
import wx.xrc as xrc

import wx.grid

import wx_utils, relpath, rst_creator, rwkos, txt_mixin, txt_database, datetime
import xml_utils
from xml_utils import prettify
import ind_grade_mapper

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

        control_attr_list = ['coursechoice','lab_number_box','team_grades_folder_box',\
                             'lab_title_box']
        self.create_xml('course_prep_gui', control_attr_list)
        
        print('xml_path = ' + xml_path)
        xml_utils.write_pretty_xml(self.xml, xml_path)


    def load(self, event=None):
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           start_dir=git_dir, \
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

    def _browse(self, save_box, msg):
        mypath = wx_utils.my_file_dialog(parent=None,\
                                         #start_dir=course_dir,\
                                         msg=msg, \
                                         )
        if mypath:
            #rp = relpath.relpath(folder_path, base=course_dir)
            save_box.SetValue(mypath)


    def get_team_grade_labels(self):
        mypath = self.team_grades_folder_box.GetValue()
        if mypath:
            print("mypath = " + mypath)
            myfile = txt_mixin.delimited_txt_file(mypath)
            labels = myfile.array[0,:]
            return labels
        return None


    def update_grade_cols(self):
        print("in update_grade_cols")
        labels = self.get_team_grade_labels()
        if labels is not None:
            self.team_grades_listbox.Clear()
            self.team_grades_listbox.Append(labels)
            

    def on_team_grade_browse(self, event=None):
        msg = "Choose the team grades spreadsheet"
        self._browse(self.team_grades_folder_box, msg)
        self.update_grade_cols()
        

    def on_team_list_browse(self, event=None):
        msg = "Choose the team list spreadsheet"
        self._browse(self.team_list_folder_box, msg)

        
        
    def my_init(self):
        print("hello");
        team_csv_path = self.search_for_bb_teamlist()
        if team_csv_path is not None:
            self.team_list_folder_box.SetValue(team_csv_path)
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
            

    def go(self, event=None):
        print("going....")
        team_grades_csv_path = self.team_grades_folder_box.GetValue()
        team_list_csv_path = self.team_list_folder_box.GetValue()
        if not team_list_csv_path:
            # exit
            return None
        labels = self.get_team_grade_labels()
        team_label = self.find_team_label(team_list_csv_path)
        print("team_label: " + team_label)
        assert team_label is not None, \
               "did not find exactly one match for [Tt]eam: " + str(labels)
        print("step 1")        
        student_to_team = ind_grade_mapper.student_to_team_mapper(team_list_csv_path, team_label)
        print("step 2")
        ind = self.team_grades_listbox.GetSelection()
        print("step 3")
        print("ind = " + str(ind))
        if ind < 0:
            return None
        col_str = self.team_grades_listbox.GetString(ind)
        print("col_str = " + col_str)
        mycols = [col_str]
        print("step 4")
        team_label2 = self.find_team_label(team_grades_csv_path)
        print("team_label2: " + team_label2)
        team_grades = ind_grade_mapper.multiple_team_grades(team_grades_csv_path, \
                                                            team_label2, \
                                                            mycols)
        print("step 5")
        outname = "ind_mapped_" + col_str + ".csv"
        outname = rwkos.clean_filename(outname)
        print("outname: " + outname)
        ind_mapper = ind_grade_mapper.ind_grade_mapper_v2(team_list_csv_path, \
                                                          student_to_team, \
                                                          team_grades, \
                                                          outname)
        ind_mapper.map_grades()
        ind_mapper.save()
        

    def OnActivate(self, evt):
        print("in OnActivate")


    def search_for_bb_teamlist(self):
        """Search in the current directory and up the tree for
        '*bb*download*team*.csv'"""
        csv_pat = "*bb*download*team*.csv"
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
        xrcfile = '/Users/kraussry/git/wxpython_guis/team_spreadsheet_mapper_xrc.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"main_panel")

        self.team_grades_folder_box = xrc.XRCCTRL(self.frame,"team_grades_folder_box")
        self.team_grades_browse = xrc.XRCCTRL(self.frame, "team_grades_browse")
        self.team_list_browse = xrc.XRCCTRL(self.frame, "team_list_browse")
        self.team_list_folder_box = xrc.XRCCTRL(self.frame,"team_list_folder_box")
        self.team_grades_listbox = xrc.XRCCTRL(self.frame,"list_box_1")
        self.go_button = xrc.XRCCTRL(self.frame, "go_button")
        #self.lab_title_box.SetFocus()
        
        wx.EVT_BUTTON(self.team_grades_browse, self.team_grades_browse.GetId(), \
                      self.on_team_grade_browse)
        wx.EVT_BUTTON(self.team_list_browse, self.team_list_browse.GetId(), \
                      self.on_team_list_browse)
        wx.EVT_BUTTON(self.go_button, self.go_button.GetId(), \
                      self.go)

        self.menubar = self.frame.GetMenuBar()
        ## self.frame.Bind(wx.EVT_MENU, self.on_exit, \
        ##                 id=xrc.XRCID('quit_menu_item'))

        self.frame.Bind(wx.EVT_MENU, self.go, \
                        id=xrc.XRCID('menu_go'))
        self.frame.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        
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
        self.frame.SetClientSize((625,300))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()


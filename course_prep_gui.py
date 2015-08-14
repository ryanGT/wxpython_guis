#!/usr/bin/env python
from __future__ import print_function

# Used to guarantee to use at least Wx2.8
import wxversion
wxversion.ensureMinimal('2.8')

import sys, time, os, gc

import wx
import wx.xrc as xrc

import wx.grid

import wx_utils, relpath, rst_creator, rwkos, txt_mixin
import xml_utils
from xml_utils import prettify

xml_wildcard = "XML files (*.xml)|*.xml"

import re

from lecture_wx_utils import *

import file_finder

import pdb

template = """=====================
    RC Circuit Modeling
=====================

ME 458 Lecture 6
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Author: Dr. Ryan Krauss

.. include:: /Users/rkrauss/git/report_generation/beamer_header.rst



Learning Outcomes
===================

Students will

"""

def suggest_lecture_number(course):
    course_root = course_roots[course]
    glob_pat = 'ME*%s*lecture*.rst' % course
    myfinder = file_finder.Glob_File_Finder(course_root,glob_pat)
    myfinder.Find_All_Files()

    lect_ints = []

    for curpath in myfinder.all_files:
        folder, curfile = os.path.split(curpath)
        q = p1.search(curfile)
        if q is not None:
            cur_int = int(q.group(2))
            lect_ints.append(cur_int)

    return max(lect_ints)+1
                          


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

        control_attr_list = ['coursechoice','lecture_number_box','root_folder_box',\
                             'lecture_title_box']
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


    def get_course(self):
        ind = self.coursechoice.GetCurrentSelection()
        course = self.coursechoice.GetString(ind)
        return course


    def get_title(self):
        title = self.lecture_title_box.GetValue()
        return title.encode()
    
        
    def set_lecture_number(self):
        course = self.get_course()
        #print('course = %s' % course)
        new_num = suggest_lecture_number(course)
        self.lecture_number_box.SetValue(str(new_num))


    def get_lecture_number(self):
        lect_num_str = self.lecture_number_box.GetValue()
        return lect_num_str
        
        
    def on_course_choice(self, event):
        print('hello from on_course_choice')
        self.set_lecture_number()


    def get_course_dir(self):
        course = self.get_course()
        course_dir = course_roots[course]
        out_dir = os.path.realpath(course_dir)
        return out_dir


    def on_browse(self, event=None):
        course_dir = self.get_course_dir()
        folder_path = wx_utils.my_dir_dialog(parent=None,\
                                             start_dir=course_dir,\
                                             msg="Choose root directory", \
                                             )
        if folder_path:
            rp = relpath.relpath(folder_path, base=course_dir)
            self.root_folder_box.SetValue(rp)

        
    def my_init(self):
        self.set_lecture_number()


    def get_subfolder(self):
        course_dir = self.get_course_dir()
        lecture_title = self.lecture_title_box.GetValue()
        subfolder = rwkos.clean_filename(lecture_title)
        lect_num = int(self.get_lecture_number())
        subfolder_out = 'lecture_%0.2i_%s' % (lect_num, subfolder)
        return subfolder_out


    def build_rst(self):
        myfile = rst_creator.rst_file()
        #pdb.set_trace()
        title = self.get_title()
        myfile.add_title(title)

        course = self.get_course()
        lect_num = int(self.get_lecture_number())
        subtitle = 'ME %s Lecture %s' % (course, lect_num)
        subtitle = subtitle.encode()
        myfile.add_subtitle(subtitle)
        myfile.add_body(':Author: Dr. Ryan Krauss')
        myfile.add_body('.. include:: /Users/rkrauss/git/report_generation/beamer_header.rst')
        myfile.add_section('Learning Outcomes')
        myfile.add_body('Students will')
        return myfile.list


    def next_lecture(self, event=None):
        self.lecture_title_box.SetValue("")
        self.set_lecture_number()
        

    def go(self, event=None):
        # 0. check for valid entries
        #    - exit if not happy
        #    - possibly share a reason with the user
        # 1. make subfolder
        # 2. create rst
        #    - creat title
        #    - create subtitle
        #    - add beamer handout header
        #    - add author
        #    - add learning outcomes slide
        subfolder = self.get_subfolder()
        print('subfolder = ' + subfolder)
        rp = self.root_folder_box.GetValue()
        path1 = os.path.join(self.get_course_dir(), rp)
        subfolder_path = os.path.join(path1, subfolder)
        if not os.path.exists(subfolder_path):
            os.mkdir(subfolder_path)

        course = self.get_course()
        rst_name = 'ME_%s_%s.rst' % (course, subfolder)
        print('rst_name = ' + rst_name)
        rst_path = os.path.join(subfolder_path, rst_name)
        print('rst_path = ' + rst_path)

        rst_list = self.build_rst()

        txt_mixin.dump(rst_path, rst_list)
            
        
        
    def OnInit(self):
        """Initialize the :py:class:`MyApp` instance; start by loading
        the xrc resource file and then add other stuff and bind the events"""
        xrcfile = 'course_prep_xrc2.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"main_panel")

        self.coursechoice = xrc.XRCCTRL(self.frame,"course_choice")
        self.lecture_number_box = xrc.XRCCTRL(self.frame,"lecture_number_box")
        self.root_folder_box = xrc.XRCCTRL(self.frame,"root_folder_box")
        self.root_browse = xrc.XRCCTRL(self.frame, "root_browse")
        self.go_button = xrc.XRCCTRL(self.frame, "go_button")
        self.next_button = xrc.XRCCTRL(self.frame, "next_button")
        self.lecture_title_box = xrc.XRCCTRL(self.frame, "lecture_title_box")
        
        wx.EVT_CHOICE(self.coursechoice, self.coursechoice.GetId(), \
                      self.on_course_choice)
        wx.EVT_BUTTON(self.root_browse, self.root_browse.GetId(), \
                      self.on_browse)
        wx.EVT_BUTTON(self.go_button, self.go_button.GetId(), \
                      self.go)
        wx.EVT_BUTTON(self.next_button, self.next_button.GetId(), \
                      self.next_lecture)

        self.menubar = self.frame.GetMenuBar()
        ## self.frame.Bind(wx.EVT_MENU, self.on_exit, \
        ##                 id=xrc.XRCID('quit_menu_item'))

        self.frame.Bind(wx.EVT_MENU, self.save, \
                        id=xrc.XRCID('menu_save'))
        self.frame.Bind(wx.EVT_MENU, self.load, \
                        id=xrc.XRCID('menu_load'))


        ## self.frame.Bind(wx.EVT_MENU, self.load, \
        ##         id=xrc.XRCID('load_menu_item'))

        self.my_init()
        self.frame.SetClientSize((625,300))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()


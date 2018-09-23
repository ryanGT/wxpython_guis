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

xml_wildcard = "XML files (*.xml)|*.xml"

import re

from lecture_wx_utils import course_roots, lecture_roots, lab_root
template_dir = '/Users/kraussry/gdrive_teaching/general_teaching/lab_templates'

import file_finder

import pdb

template = """=====================
    RC Circuit Modeling
=====================

ME 458 Lab 6
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:Author: Dr. Ryan Krauss

.. include:: /Users/rkrauss/git/report_generation/beamer_header.rst



Learning Outcomes
===================

Students will

"""


def suggest_lab_number(course):
    glob_pat = os.path.join(lab_root, 'lab_*')
    all_matches = glob.glob(glob_pat)
    lab_pat = re.compile('lab_([0-9]+)_')

    if not all_matches:
        return 1

    lab_ints = []
    
    for curpath in all_matches:
        folder, curfile = os.path.split(curpath)
        q = lab_pat.search(curfile)
        if q is not None:
            cur_int = int(q.group(1))
            lab_ints.append(cur_int)

    return max(lab_ints)+1


def find_and_replace_one_file(inpath, outpath, repdict):
    curfile = txt_mixin.txt_file_with_list(inpath)
    for key, value in repdict.items():
        curfile.replaceall(key, value)

    if not os.path.exists(outpath):
        curfile.save(outpath)
    else:
        print('file already exists: %s' % outpath)



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

        control_attr_list = ['coursechoice','lab_number_box','root_folder_box',\
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


    def get_course(self):
        ind = self.coursechoice.GetCurrentSelection()
        course = self.coursechoice.GetString(ind)
        return course


    def get_title(self):
        title = self.lab_title_box.GetValue()
        return title.encode()


    def set_lab_number(self):
        course = self.get_course()
        #print('course = %s' % course)
        new_num = suggest_lab_number(course)
        self.lab_number_box.SetValue(str(new_num))


    def get_lab_number(self):
        lab_num_str = self.lab_number_box.GetValue()
        return lab_num_str
        
        
    def on_course_choice(self, event):
        print('hello from on_course_choice')
        self.set_lab_number()


    def get_course_dir(self):
        course = self.get_course()
        course_dir = course_root[course]
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
        self.set_lab_number()


    def get_subfolder(self):
        #course_dir = self.get_course_dir()
        lab_title = self.lab_title_box.GetValue()
        subfolder = rwkos.clean_filename(lab_title)
        lab_num = int(self.get_lab_number())
        subfolder_out = 'lab_%0.2i_%s' % (lab_num, subfolder)
        return subfolder_out


    def build_rst(self):
        myfile = rst_creator.rst_file()
        #pdb.set_trace()
        title = self.get_title()
        myfile.add_title(title)

        course = self.get_course()
        lab_num = int(self.get_lab_number())
        subtitle = 'ME %s Lab %s' % (course, lab_num)
        subtitle = subtitle.encode()
        myfile.add_subtitle(subtitle)
        myfile.add_body(':Author: Dr. Ryan Krauss')
        myfile.add_body('.. include:: /Users/rkrauss/git/report_generation/beamer_header.rst')
        myfile.add_section('Learning Outcomes')
        myfile.add_body('Students will')
        return myfile.list


    def next_lab(self, event=None):
        self.lab_title_box.SetValue("")
        self.set_lab_number()


    def build_repdict(self):
        """Find the values that need to be replaced in lab
        template tex and md files and put them in a dictionary for
        find and replace."""
        subfolder = self.get_subfolder()
        print('subfolder = ' + subfolder)
        rp = self.root_folder_box.GetValue()
        path1 = os.path.join(lab_root, rp)
        lab_folder_path = os.path.join(path1, subfolder)
        print('lab_folder_path = %s' % lab_folder_path)
        self.lab_folder_path = lab_folder_path
        self.subfolder = subfolder
        coursenum = self.coursechoice.GetStringSelection()
        labnum = int(self.get_lab_number())
        self.labnum = labnum
        title = self.lab_title_box.GetValue()
        lab_num = int(self.get_lab_number())
        
        #labnum_str = '%0.2i' % labnum
        labnum_str = '%i' % labnum
        two_dig_labnum = '%0.2i' % labnum
        repdict = {'%%TITLE%%': title, \
                   '%%LABNUM%%': str(labnum_str), \
                   '%%TWODIGITLABNUM%%': str(two_dig_labnum), \
                   '%%COURSENUM%%': str(coursenum), \
                   }
        self.repdict = repdict
        return repdict

        
    def prep_and_copy_procedure(self):
        inpath = os.path.join(template_dir, 'lab_procedure.md')
        outname = self.subfolder + '.md'
        outpath = os.path.join(self.lab_folder_path, outname)
        find_and_replace_one_file(inpath, outpath, self.repdict)


    def prep_and_copy_notes_md(self):
        inpath = os.path.join(template_dir, 'lab_notes.md')
        outname = 'notes_after_lab_%0.2i.md' % self.labnum
        outpath = os.path.join(self.lab_folder_path, outname)
        find_and_replace_one_file(inpath, outpath, self.repdict)

        
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
        repdict = self.build_repdict()
        rwkos.make_dir(self.lab_folder_path)#<-- variable set in build_repdict()
        self.prep_and_copy_procedure()
        self.prep_and_copy_notes_md()
        
        #if not os.path.exists(subfolder_path):
        #    os.mkdir(subfolder_path)

        course = self.get_course()
        ## rst_name = 'ME_%s_%s.rst' % (course, subfolder)
        ## print('rst_name = ' + rst_name)
        ## rst_path = os.path.join(subfolder_path, rst_name)
        ## print('rst_path = ' + rst_path)

        ## rst_list = self.build_rst()

        ## txt_mixin.dump(rst_path, rst_list)
            

    def OnActivate(self, evt):
        self.lab_title_box.SetFocus()
        
        
    def OnInit(self):
        """Initialize the :py:class:`MyApp` instance; start by loading
        the xrc resource file and then add other stuff and bind the events"""
        xrcfile = '/Users/kraussry/git/wxpython_guis/lab_prep_xrc_GVSU.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"main_panel")

        self.coursechoice = xrc.XRCCTRL(self.frame,"course_choice")
        self.coursechoice.SetStringSelection('345')
        self.lab_number_box = xrc.XRCCTRL(self.frame,"lab_number_box")
        self.root_folder_box = xrc.XRCCTRL(self.frame,"root_folder_box")
        self.root_browse = xrc.XRCCTRL(self.frame, "root_browse")
        self.go_button = xrc.XRCCTRL(self.frame, "go_button")
        self.next_button = xrc.XRCCTRL(self.frame, "next_button")
        self.lab_title_box = xrc.XRCCTRL(self.frame, "lab_title_box")
        self.lab_title_box.SetFocus()
        
        wx.EVT_CHOICE(self.coursechoice, self.coursechoice.GetId(), \
                      self.on_course_choice)
        wx.EVT_BUTTON(self.root_browse, self.root_browse.GetId(), \
                      self.on_browse)
        wx.EVT_BUTTON(self.go_button, self.go_button.GetId(), \
                      self.go)
        wx.EVT_BUTTON(self.next_button, self.next_button.GetId(), \
                      self.next_lab)

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
        L4title = "Open-Loop DC Motor Control"
        self.lab_title_box.SetValue(L4title)
        self.frame.SetClientSize((625,300))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()


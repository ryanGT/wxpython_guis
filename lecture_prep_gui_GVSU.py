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

from lecture_wx_utils import course_roots, lecture_roots
template_dir = '/Users/kraussry/gdrive_teaching/general_teaching/lecture_templates'

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


# build dictionary to look up date from lecture number
dates_path = '/Users/kraussry/gdrive_teaching/345_F18/lectures/dates_look_up.tsv'
datesdb = txt_database.txt_database_from_file(dates_path)
dates_dict =  dict(zip(datesdb.Class, datesdb.Date))


def suggest_lecture_number(course):
    lectures_root = lecture_roots[course]
    glob_pat = os.path.join(lectures_root, 'lecture_*')
    all_matches = glob.glob(glob_pat)
    lect_pat = re.compile('lecture_([0-9]+)_')

    if not all_matches:
        return 1

    lect_ints = []
    
    for curpath in all_matches:
        folder, curfile = os.path.split(curpath)
        q = lect_pat.search(curfile)
        if q is not None:
            cur_int = int(q.group(1))
            lect_ints.append(cur_int)

    return max(lect_ints)+1


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


    def guess_date(self):
        lect_num_str = self.lecture_number_box.GetValue()
        date_str_1 = dates_dict[lect_num_str]#<-- month/day
        #get year str
        now = datetime.datetime.now()
        year_str = str(now.year)[-2:]
        full_date_str = '%s/%s' % (date_str_1, year_str)
        return full_date_str
        

    def set_date_str(self):
        lect_num_str = self.lecture_number_box.GetValue()
        if lect_num_str:
            self.lecture_date_box.SetValue(self.guess_date())
            

    def get_date_str(self):
        dstr = self.lecture_date_box.GetValue()
        return dstr
        
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


    def get_lectures_dir(self):
        course = self.get_course()
        course_dir = lecture_roots[course]
        out_dir = os.path.realpath(course_dir)#<-- do I want this?  or
                                              #trust good paths in lecture_wx_utils?
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
        self.set_date_str()

    def get_subfolder(self):
        #course_dir = self.get_course_dir()
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


    def build_repdict(self):
        """Find the values that need to be replaced in lecture
        template tex and md files and put them in a dictionary for
        find and replace."""
        subfolder = self.get_subfolder()
        print('subfolder = ' + subfolder)
        rp = self.root_folder_box.GetValue()
        path1 = os.path.join(self.get_lectures_dir(), rp)
        lect_folder_path = os.path.join(path1, subfolder)
        print('lect_folder_path = %s' % lect_folder_path)
        self.lect_folder_path = lect_folder_path
        self.subfolder = subfolder
        coursenum = self.coursechoice.GetStringSelection()
        lectnum = int(self.get_lecture_number())
        self.lectnum = lectnum
        title = self.lecture_title_box.GetValue()
        lect_num = int(self.get_lecture_number())
        date_str = self.get_date_str()
        
        #lectnum_str = '%0.2i' % lectnum
        lectnum_str = '%i' % lectnum
        two_dig_lectnum = '%0.2i' % lectnum
        repdict = {'%%TITLE%%': title, \
                   '%%LECTNUM%%': str(lectnum_str), \
                   '%%TWODIGITLECTNUM%%': str(two_dig_lectnum), \
                   '%%COURSENUM%%': str(coursenum), \
                   '%%DATE%%':date_str}
        self.repdict = repdict
        return repdict

        
    def prep_and_copy_slides_main_tex(self):
        inpath = os.path.join(template_dir, 'slides_main_template.tex')
        outname = 'lecture_%0.2i_slides_main.tex' % self.lectnum
        outpath = os.path.join(self.lect_folder_path, outname)
        find_and_replace_one_file(inpath, outpath, self.repdict)


    def prep_and_copy_top_level_md(self):
        inpath = os.path.join(template_dir, 'top_level_outline_template.md')
        outname = 'lecture_%0.2i_top_level_outline.md' % self.lectnum
        outpath = os.path.join(self.lect_folder_path, outname)
        find_and_replace_one_file(inpath, outpath, self.repdict)


    def prep_and_copy_graph_paper(self):
        inpath = os.path.join(template_dir, 'graph_paper.tex')
        outname = 'graph_paper_lecture_%0.2i.tex' % self.lectnum
        outpath = os.path.join(self.lect_folder_path, outname)
        find_and_replace_one_file(inpath, outpath, self.repdict)
        curdir = os.getcwd()
        try:
            os.chdir(self.lect_folder_path)
            cmd = 'pdflatex %s' % outname
            os.system(cmd)
        finally:
            os.chdir(curdir)
            

    def prep_and_copy_notes_md(self):
        inpath = os.path.join(template_dir, 'notes_after_lecture_template.md')
        outname = 'notes_after_lecture_%0.2i.md' % self.lectnum
        outpath = os.path.join(self.lect_folder_path, outname)
        find_and_replace_one_file(inpath, outpath, self.repdict)

        
    def copy_mydefs_sty(self):
        inpath = os.path.join(template_dir, 'mydefs.sty')
        outpath = os.path.join(self.lect_folder_path, 'mydefs.sty')
        if not os.path.exists(outpath):
            shutil.copyfile(inpath, outpath)


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
        rwkos.make_dir(self.lect_folder_path)#<-- variable set in build_repdict()
        self.prep_and_copy_slides_main_tex()
        self.prep_and_copy_top_level_md()
        self.prep_and_copy_notes_md()
        self.prep_and_copy_graph_paper()
        self.copy_mydefs_sty()
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
        self.lecture_title_box.SetFocus()
        
        
    def OnInit(self):
        """Initialize the :py:class:`MyApp` instance; start by loading
        the xrc resource file and then add other stuff and bind the events"""
        xrcfile = '/Users/kraussry/git/wxpython_guis/lecture_prep_xrc_GVSU.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"main_panel")

        self.coursechoice = xrc.XRCCTRL(self.frame,"course_choice")
        self.coursechoice.SetStringSelection('345')
        self.lecture_number_box = xrc.XRCCTRL(self.frame,"lecture_number_box")
        self.lecture_date_box = xrc.XRCCTRL(self.frame,"lecture_date_box")
        self.root_folder_box = xrc.XRCCTRL(self.frame,"root_folder_box")
        self.root_browse = xrc.XRCCTRL(self.frame, "root_browse")
        self.go_button = xrc.XRCCTRL(self.frame, "go_button")
        self.next_button = xrc.XRCCTRL(self.frame, "next_button")
        self.lecture_title_box = xrc.XRCCTRL(self.frame, "lecture_title_box")
        self.lecture_title_box.SetFocus()
        
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
        self.frame.SetClientSize((625,300))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()


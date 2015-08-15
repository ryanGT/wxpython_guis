#!/usr/bin/env python
from __future__ import print_function

# Used to guarantee to use at least Wx2.8
import wxversion
wxversion.ensureMinimal('2.8')

import sys, time, os, gc, glob, shutil, re

import wx
import wx.xrc as xrc

import wx.grid

import wx_utils, relpath, rst_creator, rwkos, txt_mixin
import xml_utils
from xml_utils import prettify

xml_wildcard = "XML files (*.xml)|*.xml"

import re


from lecture_wx_utils import p1, git_dir, semester_root, course_roots, \
     lecture_roots, course_class_dict
import lecture_utils

lecture_num_pat = re.compile('lecture_*([0-9]+)')
date_folder_pat = re.compile('\d\d_\d\d_\d\d')

import file_finder

import pdb

class MyApp(wx.App, wx_utils.gui_that_saves):
    def save(self, event=None):
        course = self.get_course()
        xml_name = 'lecture_copy_%s.xml' % course
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
        ind = self.course_choice.GetCurrentSelection()
        course = self.course_choice.GetString(ind)
        return course


    def on_course_choice(self, event=None):
        print('hello from on_course_choice')
        self.get_lecture_date_folder()
        

    def on_course_1(self, event=None):
        self.course_choice.SetSelection(0)        
        self.on_course_choice(event=event)
        

    def on_course_2(self, event=None):
        self.course_choice.SetSelection(1)        
        self.on_course_choice(event=event)
        
        
    def get_course_dir(self):
        course = self.get_course()
        course_dir = course_roots[course]
        out_dir = os.path.realpath(course_dir)
        return out_dir


    def get_lectures_dir(self):
        course = self.get_course()
        lectures_dir = lecture_roots[course]
        out_dir = os.path.realpath(lectures_dir)
        return out_dir


    def get_lectures_date_folder_from_textbox(self):
        rp = self.dest_dir_box.GetValue()
        rp = rp.encode()
        date_folder_path = os.path.join(semester_root, rp)
        return date_folder_path
    

    def _get_lecture_date_folder(self):
        """Get the path to the lectures/mm_dd_yy folder.  Note this
        does not actually read what is in the text box, but determines
        what the next lecture should be.  This could be problematic if
        you were trying to work ahead."""
        course = self.get_course()
        myclass = course_class_dict[course]
        mycouse = myclass()
        folder_path = mycouse.build_lecture_path_string()
        return folder_path


    def check_for_existing_lecture_folder(self):
        #folder_path = self._get_lecture_date_folder()
        folder_path = self.get_lectures_date_folder_from_textbox()
        mybool = os.path.exists(folder_path)
        self.lecure_folder_exists_check.SetValue(mybool)
        return mybool

        
    def get_lecture_date_folder(self):
        folder_path = self._get_lecture_date_folder()
        #print('folder_path = %s' % folder_path)
        rp = relpath.relpath(folder_path, base=semester_root)
        self.dest_dir_box.SetValue(rp)
        self.check_for_existing_lecture_folder()
        return folder_path


    def on_make_lecture_date_folder(self, event=None):
        #folder_path = self._get_lecture_date_folder()
        folder_path = self.get_lectures_date_folder_from_textbox()
        if not os.path.exists(folder_path):
            os.mkdir(folder_path)
            
        self.check_for_existing_lecture_folder()

        
    def get_source_path(self):
        rp = self.source_dir_box.GetValue()
        full_source_path = os.path.join(semester_root, rp)
        return full_source_path


    def source_glob(self, pat):
        source_dir = self.get_source_path()
        full_pat = os.path.join(source_dir, pat)
        myfiles = glob.glob(full_pat)
        rp_list = [relpath.relpath(item, base=source_dir) for item in myfiles]
        return rp_list
    
        
    def list_source_dir(self):
        pdflist = self.source_glob('*.pdf')
        handout_name, other_pdfs = lecture_utils.list_pdfs_find_handout(pdflist)
        if handout_name is not None:
            self.has_handout = True
            all_pdfs = [handout_name] + other_pdfs
        else:
            self.has_handout = False
            all_pdfs = other_pdfs
            
        all_items = all_pdfs

        other_exts = ['*.py','*.m']

        for ext in other_exts:
            curfiles = self.source_glob(ext)
            if curfiles:
                all_items.extend(curfiles)
            
        self.source_files_list.Clear()
        self.source_files_list.SetItems(all_items)


    def guess_lecture_number(self):
        src_dir = self.get_src_dir()
        junk, src_folder = os.path.split(src_dir)
        print('src_folder = ' + src_folder)
        q = lecture_num_pat.search(src_folder)
        if q:
            lect_num_str = q.group(1)
            lect_num = int(lect_num_str)#convert to int to drop leading zeros
            return lect_num


    def set_lecture_number(self, lect_num=None):
        if lect_num is None:
            lect_num = self.guess_lecture_number()
        if lect_num is not None:
            self.dest_lecture_number_box.SetValue(str(lect_num))
        
        
    def on_browse_source(self, event=None):
        course_dir = self.get_course_dir()
        folder_path = wx_utils.my_dir_dialog(parent=None, \
                                             start_dir=course_dir, \
                                             msg="Choose source directory", \
                                             )
        if folder_path:
            rp = relpath.relpath(folder_path, base=semester_root)
            self.source_dir_box.SetValue(rp)
            self.list_source_dir()
            self.set_lecture_number()



    def on_browse_dest(self, event=None):
        lectures_dir = self.get_lectures_dir()
        folder_path = wx_utils.my_dir_dialog(parent=None, \
                                             start_dir=lectures_dir, \
                                             msg="Choose destination directory", \
                                             )
        if folder_path:
            rp = relpath.relpath(folder_path, base=semester_root)
            self.dest_dir_box.SetValue(rp)
        
    
    def my_init(self):
        case = 1
        if case == 1:
            #case 1: 458
            self.on_course_2()
            self.get_lecture_date_folder()
            self.source_dir_box.SetValue('458_Fall_2015/prep/part_01_intro_to_course_and_python/lecture_1_2_intro_to_python')
            self.list_source_dir()
            self.set_lecture_number()
            self.dest_lecture_title_box.SetValue('Intro to 458 and Intro to Python Part 1')
        elif case == 2:
            self.on_course_1()
            self.source_dir_box.SetValue('450_Fall_2015/prep/lecture_01')
            self.list_source_dir()
            self.set_lecture_number()
            self.dest_lecture_title_box.SetValue('Intro to 450 and Review of 356')
        

    def get_dst_dir(self, www=False):
        rp = self.dest_dir_box.GetValue()
        if www:
            www_path = os.path.join(semester_root, 'www')
            dest_path = os.path.join(www_path,rp)
        else:
            dest_path = os.path.join(semester_root,rp)
        return dest_path


    def get_src_dir(self):
        rp = self.source_dir_box.GetValue()
        src_path = os.path.join(semester_root,rp)
        return src_path


    def get_filenames(self):
        ctrl = self.source_files_list
        N = ctrl.GetCount()

        filenames = []

        for i in range(N):
            curstring = ctrl.GetString(i)
            filenames.append(curstring)

        return filenames


    def get_overwrite(self):
        mybool = self.overwrite_check.GetValue()
        return mybool
    

    def copy(self, event=None):
        src_dir = self.get_src_dir()
        dst_dir = self.get_dst_dir()
        filenames = self.get_filenames()
        overwrite = self.get_overwrite()
        #print('src_dir = ' + src_dir)
        #print('dst_dir = ' + dst_dir)
        #print('filenames:')
        for item in filenames:
            dst_path = os.path.join(dst_dir, item)
            src_path = os.path.join(src_dir, item)
            src_exists = os.path.exists(src_path)
            dst_exists = os.path.exists(dst_path)
            if src_dir:
                if overwrite or not dst_exists:
                    shutil.copy2(src_path, dst_path)


    def go(self, event=None):
        self.on_make_lecture_date_folder(event=event)
        self.copy(event=event)
        self.make_index_dest(event=event)
        self.append_lectures_rst()
        self.on_menu_sphinx_build()

    def on_menu_go(self, event=None):
        self.go(event=event)
        

    def _open_terminal(self, folder_path):
        cmd = 'open -a Terminal %s' % folder_path
        os.system(cmd)

        
    def open_terminal_dst(self, event=None):
        dst_folder = self.get_dst_dir()
        self._open_terminal(dst_folder)


    def open_terminal_src(self, event=None):
        src_folder = self.get_src_dir()
        self._open_terminal(src_folder)


    def _execute_cmd_in_dir(self, cmd, exe_dir):
        curdir = os.getcwd()
        os.chdir(exe_dir)
        os.system(cmd)
        os.chdir(curdir)
        

    def _make_index(self, exe_dir, download=False, title=None):
        cmd = 'make_index.py'
        if download:
            cmd += ' -d'
        if title:
            cmd += ' -t "%s"' % title
        self._execute_cmd_in_dir(cmd, exe_dir)
        

    def build_dest_title(self):
        title_pat = 'Lecture %s: %s (%s)'
        main_str = self.dest_lecture_title_box.GetValue()
        lect_num_str = self.dest_lecture_number_box.GetValue()
        dst_folder = self.get_dst_dir()
        junk, foldername = os.path.split(dst_folder)
        date_q = date_folder_pat.search(foldername)
        date_str = date_q.group().replace('_','/')
        full_title = title_pat % (lect_num_str, main_str, date_str)
        return full_title


    def append_lectures_rst(self):
        # find lectures dir
        lectures_dir = self.get_lectures_dir()
        rst_path = os.path.join(lectures_dir, 'lectures.rst')
        if not os.path.exists(rst_path):
            print('rst_path does not exist: ' + rst_path)
            return None
        myfile = txt_mixin.txt_file_with_list(rst_path)
        full_date_path = self.get_lectures_date_folder_from_textbox()
        junk, date_folder = os.path.split(full_date_path)
        inds = myfile.list.findall(date_folder)
        if inds:
            #already in, do nothing
            return None
        else:
            while not myfile.list[-1]:
                myfile.list.pop(-1)
            index_rp = os.path.join(date_folder, 'index.rst')
            outline = ' '*3 + index_rp
            myfile.list.append(outline)
            myfile.list.append('')
            myfile.save(rst_path)


    def on_menu_append_lectures_rst(self, event=None):
        self.append_lectures_rst()
        
        
    def make_index_dest(self, event=None):
        dst_folder = self.get_dst_dir()
        title = self.build_dest_title()
        self._make_index(dst_folder, download=True, title=title)


    def make_index_src(self, event=None):
        src_folder = self.get_src_dir()
        self._make_index(src_folder)

        
    def make_outline(self, event=None):
        course = self.get_course()
        myclass = course_class_dict[course]
        mycourse = myclass()
        mycourse.run()


    def open_finder_folder(self, folder):
        cmd = 'open %s' % folder
        os.system(cmd)


    def on_menu_finder_dest(self, event=None):
        folder = self.get_dst_dir()
        self.open_finder_folder(folder)
        
    
    def on_menu_finder_src(self, event=None):
        folder = self.get_src_dir()
        self.open_finder_folder(folder)


    def open_emacs_path(self, filepath):
        cmd = 'emacs %s &' % filepath
        print(cmd)
        os.system(cmd)


    def _get_exlude_folder_path(self):
        folder = self.get_dst_dir()
        exclude_folder = os.path.join(folder, 'exclude')
        return exclude_folder
    

    def on_menu_emacs_exclude_outline(self, event=None):
        exclude_folder = self._get_exlude_folder_path()
        outline_path = os.path.join(exclude_folder, 'outline.rst')
        self.open_emacs_path(outline_path)
        

    def on_menu_emacs_src_index(self, event=None):
        src_folder = self.get_src_dir()
        src_index_path = os.path.join(src_folder, 'index.rst')
        self.open_emacs_path(src_index_path)


    def on_menu_emacs_dest_index(self, event=None):
        dst_folder = self.get_dst_dir()
        dst_index_path = os.path.join(dst_folder, 'index.rst')
        self.open_emacs_path(dst_index_path)


    def open_html(self, html_path):
        cmd = 'open %s' % html_path
        os.system(cmd)


    def open_index_in_folder(self, folder_path):
        html_path = os.path.join(folder_path, 'index.html')
        self.open_html(html_path)

        
    def on_menu_view_html_src(self, event=None):
        src_folder = self.get_src_dir()
        self.open_index_in_folder(src_folder)
        outline_path = os.path.join(src_folder, 'outline.html')
        if os.path.exists(outline_path):
            self.open_html(outline_path)
        

    def on_menu_view_html_dest(self, event=None):
        dst_folder = self.get_dst_dir(www=True)
        self.open_index_in_folder(dst_folder)


    def on_menu_outline_exclude_s5(self, event=None):
        exclude_folder = self._get_exlude_folder_path()
        outline_s5_path = os.path.join(exclude_folder, 'outline_s5.html')
        self.open_html(outline_s5_path)

    def on_menu_sphinx_build(self, event=None):
        cmd = 'make_website.py'
        print('semester_root = ' + semester_root)
        self._execute_cmd_in_dir(cmd, semester_root)
        

    def on_menu_rst2lecture_outline(self, event=None):
        exclude_folder = self._get_exlude_folder_path()
        cmd = 'rst2lecture_outline.py'
        self._execute_cmd_in_dir(cmd, exclude_folder)


    def get_src_outline_path(self):
        src_folder = self.get_src_dir()
        outline_name = 'outline.rst'
        outline_path = os.path.join(src_folder, outline_name)
        return outline_path


    def check_for_src_outline_path(self):
        outline_path = self.get_src_outline_path()
        mybool = os.path.exists(outline_path)
        return mybool

    
    def on_menu_rst2html_src(self, event=None):
        src_folder = self.get_src_dir()
        cmd = 'rst2html_rwk.py index.rst'
        self._execute_cmd_in_dir(cmd, src_folder)
        if self.check_for_src_outline_path():
            cmd2 = 'rst2html_rwk.py outline.rst'
            self._execute_cmd_in_dir(cmd2, src_folder)
            


    def on_exit(self, event=None):
        print('exiting')
        self.frame.Close(True)  # Close the frame.    

        
    def OnInit(self):
        """Initialize the :py:class:`MyApp` instance; start by loading
        the xrc resource file and then add other stuff and bind the events"""
        xrcfile = 'lecture_prep_copy_xrc.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"main_panel")

        #self.course_choice = xrc.XRCCTRL(self.frame,"course_choice")
        xrc_list = ['source_dir_box','course_choice', \
                    'source_browse_button','source_files_list', \
                    'dest_browse_button','dest_dir_box', \
                    'lecure_folder_exists_check', \
                    'make_lecture_folder_button', \
                    'copy_button', 'overwrite_check', \
                    'dest_lecture_number_box', \
                    'dest_lecture_title_box', \
                    'go_button', \
                    ]

        for label in xrc_list:
            ctrl = xrc.XRCCTRL(self.frame, label)
            setattr(self, label, ctrl)
            
        wx.EVT_CHOICE(self.course_choice, self.course_choice.GetId(), \
                      self.on_course_choice)
        wx.EVT_BUTTON(self.source_browse_button, \
                      self.source_browse_button.GetId(), \
                      self.on_browse_source)
        wx.EVT_BUTTON(self.dest_browse_button, \
                      self.dest_browse_button.GetId(), \
                      self.on_browse_dest)
        wx.EVT_BUTTON(self.make_lecture_folder_button, \
                      self.make_lecture_folder_button.GetId(), \
                      self.on_make_lecture_date_folder)
        wx.EVT_BUTTON(self.copy_button, \
                      self.copy_button.GetId(), \
                      self.copy)
        wx.EVT_BUTTON(self.go_button, \
                      self.go_button.GetId(), \
                      self.go)
        
        ## wx.EVT_BUTTON(self.go_button, self.go_button.GetId(), \
        ##               self.go)
        ## wx.EVT_BUTTON(self.next_button, self.next_button.GetId(), \
        ##               self.next_lecture)

        self.menubar = self.frame.GetMenuBar()
        self.frame.Bind(wx.EVT_MENU, self.on_exit, \
                        id=xrc.XRCID('menu_quit'))

        self.frame.Bind(wx.EVT_MENU, self.on_browse_source, \
                        id=xrc.XRCID('menu_browse_prep'))
        self.frame.Bind(wx.EVT_MENU, self.on_browse_dest, \
                        id=xrc.XRCID('menu_browse_dest'))
        self.frame.Bind(wx.EVT_MENU, self.on_course_1, \
                        id=xrc.XRCID('menu_course_1'))
        self.frame.Bind(wx.EVT_MENU, self.on_course_2, \
                        id=xrc.XRCID('menu_course_2'))
        self.frame.Bind(wx.EVT_MENU, self.on_make_lecture_date_folder, \
                        id=xrc.XRCID('menu_make_folder'))
        self.frame.Bind(wx.EVT_MENU, self.copy, \
                        id=xrc.XRCID('menu_copy'))
        self.frame.Bind(wx.EVT_MENU, self.make_index_dest, \
                        id=xrc.XRCID('menu_make_index_dest'))
        self.frame.Bind(wx.EVT_MENU, self.make_index_src, \
                        id=xrc.XRCID('menu_make_index_src'))
        self.frame.Bind(wx.EVT_MENU, self.make_outline, \
                        id=xrc.XRCID('menu_make_outline'))
        self.frame.Bind(wx.EVT_MENU, self.open_terminal_dst, \
                        id=xrc.XRCID('menu_terminal_dest'))
        self.frame.Bind(wx.EVT_MENU, self.open_terminal_src, \
                        id=xrc.XRCID('menu_terminal_src'))


        menu_list = ['menu_finder_dest', \
                     'menu_finder_src', \
                     'menu_emacs_exclude_outline', \
                     'menu_emacs_src_index', \
                     'menu_emacs_dest_index', \
                     'menu_view_html_src', \
                     'menu_view_html_dest', \
                     'menu_outline_exclude_s5', \
                     'menu_sphinx_build', \
                     'menu_rst2lecture_outline', \
                     'menu_rst2html_src', \
                     'menu_append_lectures_rst', \
                     'menu_go', \
                     ]

        # bind these to methods on_menu_finder_dest, ...
        # by prepending on_ to the names
        for item in menu_list:
            method_name = 'on_' + item
            attr = getattr(self, method_name)
            self.frame.Bind(wx.EVT_MENU, \
                            attr, \
                            id=xrc.XRCID(item))
            
        ## self.frame.Bind(wx.EVT_MENU, self.save, \
        ##                 id=xrc.XRCID('menu_save'))
        ## self.frame.Bind(wx.EVT_MENU, self.load, \
        ##                 id=xrc.XRCID('menu_load'))


        ## self.frame.Bind(wx.EVT_MENU, self.load, \
        ##         id=xrc.XRCID('load_menu_item'))

        self.my_init()
        self.frame.SetClientSize((625,500))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True


# To Do:
#
# - suggest title from main ME_4xx_*.rst file from handout
# - add menu options for removing files or moving them up and down
# - do I create a config.py file or something in each dest or src dir
#   in order to save the title and ignored files?
# - create a directory_viewer object that can be used here and elsewhere
# - move pdf from scannerpro dropbox?


if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()


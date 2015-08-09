#!/usr/bin/env python
from __future__ import print_function

# Used to guarantee to use at least Wx2.8
import wxversion
wxversion.ensureMinimal('2.8')

import sys, time, os, gc

import wx
import wx.xrc as xrc

import wx.grid

import txt_data_processing
import txt_database, txt_mixin
import copy
import pdb

data_wildcard = "Text files (*.txt; *.csv)|*.txt;*.csv|" \
                "All files (*.*)|*.*"
xml_wildcard = "XML files (*.xml)|*.xml"
png_wildcard = "PNG files (*.png)|*.png"
eps_wildcard = "EPS files (*.eps)|*.eps"
spreadsheet_wildcard = "spreadsheet files (*.csv;*.xlsx)|*.csv;*.xlsx"

import xml.etree.ElementTree as ET
from xml.dom import minidom

import xml_utils
from xml_utils import prettify

import wx_utils

import gmail_smtp

mysig = """
--
Ryan Krauss, Ph.D.
Associate Professor
Mechanical Engineering
Southern Illinois University Edwardsville"""


def check_for_blanks(arrayin):
    for item in arrayin:
        if not item:
            raise ValueError, 'blank item: ' + item
    
class MyApp(wx.App, wx_utils.gui_that_saves):
    ## def on_save_current_pd(self, event):
    ##     """Save the current plot description
    ##     (:py:attr:`MyApp.cur_plot_description`) as an XML file."""
    ##     print('in on_save_current_pd')

    ##     dlg = wx.FileDialog(self.frame, message="Save Plot Description as XML",
    ##                 defaultFile="",
    ##                 wildcard=xml_wildcard,
    ##                 style=wx.SAVE | wx.CHANGE_DIR
    ##                 )

    ##     if dlg.ShowModal() == wx.ID_OK:
    ##         root = ET.Element('plot_description_file')
    ##         self.cur_plot_description.create_xml(root)
    ##         pretty_str = prettify(root)
    ##         filename = dlg.GetFilename()
    ##         dirname = dlg.GetDirectory()
    ##         filepath = os.path.join(dirname, filename)
    ##         f = open(filepath, 'wb')
    ##         f.write(pretty_str)
    ##         f.close()

    ##     dlg.Destroy()



    ## def on_save_gui_state(self, event):
    ##     """Save the entire GUI state to an XML file"""
    ##     xml_path = wx_utils.my_file_dialog(parent=self.frame, \
    ##                                        msg="Save GUI state as", \
    ##                                        kind="save", \
    ##                                        wildcard=xml_wildcard, \
    ##                                        )
    ##     if xml_path:
    ##         root = ET.Element('data_vis_gui_state')
    ##         pd_list_xml = ET.SubElement(root, 'plot_description_list')

    ##         for key in self.plot_list:
    ##             pd = self.plot_dict[key]
    ##             pd.create_xml(pd_list_xml)


    ##         #figures
    ##         first = 1
    ##         for fig in self.figure_list:
    ##             if fig is not None:
    ##                 if first:
    ##                     first = 0
    ##                     fig_list_xml = ET.SubElement(root, 'figures')
    ##                 fig.create_xml(fig_list_xml)
                    
                            
    ##         inds = self.plot_name_list_box.GetSelections()
    ##         params_xml = ET.SubElement(root, 'gui_params')
    ##         plot_name = self.plot_name_ctrl.GetValue().encode()
    ##         inds_str = str(list(inds))
    ##         sel = self.td_bode_notebook.GetSelection()
    ##         if sel == 0:
    ##             plot_type = 'time_domain'
    ##         elif sel == 1:
    ##             plot_type = 'bode'

            
    ##         af_name = 'None'
    ##         if hasattr(self, 'active_fig'):
    ##             if self.active_fig is not None:
    ##                 af_name = self.active_fig.name
            
    ##         mydict = {'selected_inds':inds_str, \
    ##                   'active_plot_name':plot_name, \
    ##                   'plot_type':plot_type, \
    ##                   'active_fig':af_name}
                    
    ##         xml_utils.append_dict_to_xml(params_xml, mydict)
            
    ##         xml_utils.write_pretty_xml(root, xml_path)


    ## def on_load_gui_state(self, event):
    ##     """Load and reset the GUI state from an XML file"""
    ##     xml_path = wx_utils.my_file_dialog(parent=self.frame, \
    ##                                        msg="Load GUI state from XML", \
    ##                                        kind="open", \
    ##                                        wildcard=xml_wildcard, \
    ##                                        )
    ##     if xml_path:
    ##         print('xml_path = ' + xml_path)
    ##         myparser = gui_state_parser(xml_path)
    ##         myparser.parse()
    ##         myparser.convert()
    ##         for pd in myparser.pd_list:
    ##             self.add_plot_description(pd)


    ##         #set the selected plots
    ##         self.plot_name_list_box.DeselectAll()
    ##         for ind in myparser.params['selected_inds']:
    ##             self.plot_name_list_box.Select(ind)
            

    ##         #set the current/active plot
    ##         active_name = myparser.params['active_plot_name']
    ##         active_pd = self.plot_dict[active_name]
    ##         self.cur_plot_description = active_pd
    ##         self.plot_parameters_to_gui(active_pd)


    ##         # load figures here
            
    ##         # it should be true that all the plot descriptions are
    ##         # already loaded
    ##         if myparser.has_figs:
    ##             for fig in myparser.fig_list:
    ##                 ind = self.find_empty_figure()
    ##                 fig_num = ind + 1
    ##                 self.set_figure_menu_text(fig.name, fig_num)
    ##                 self.figure_list[ind] = fig

    ##             if myparser.params.has_key('active_fig'):
    ##                 active_fig_name = myparser.params['active_fig']
    ##                 ind = self.find_fig_ind(active_fig_name)

    ##             #ind will be the last ind aded if active_fig is not a
    ##             #saved parameter
    ##             self.set_active_figure(ind)

    ##         self._update_plot()

    def save(self, event=None):
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                   msg="Save GUI state as", \
                                   kind="save", \
                                   wildcard=xml_wildcard, \
                                   )

        control_attr_list = ['spreadsheet_path_box','greeting_box','body_box',\
                             'closing_box','signature_box','subject_box']
        self.create_xml('multi_email_gui', control_attr_list)

        print('xml_path = ' + xml_path)
        xml_utils.write_pretty_xml(self.xml, xml_path)


    def load(self, event=None):
        xml_path = wx_utils.my_file_dialog(parent=self.frame, \
                                   msg="Choose an xml file", \
                                   kind="open", \
                                   wildcard=xml_wildcard, \
                                   )
        self.load_xml(xml_path)
        sp_path = self.spreadsheet_path_box.GetValue()
        self.validate_spreadsheet(sp_path)
        

    def on_exit(self,event):
        """Close the GUI"""
        self.frame.Close(True)  # Close the frame.    


    def validate_spreadsheet(self, path, debug=1):
        db = txt_database.db_from_file(path)
        mylist = txt_mixin.txt_list(db.labels)
        
        def get_db_attr_by_pat(pat):
            inds = mylist.findallre(pat)
            assert len(inds) > 0, "did not find a match for %s in labels" % pat
            assert len(inds) == 1, "found more than one match for %s" %s
            ind = inds[0]
            fn_label = db.labels[ind] 
            attr = db.attr_label_dict[fn_label]
            vect = getattr(db, attr)
            return vect

        fn_pat = '[Ff]irst[ _][Nn]ame'
        try:
            self.first_names = get_db_attr_by_pat(fn_pat)
        except:
            print('delimited text file must have a column label that matches %s' % \
                  fn_pat)
        self.emails = get_db_attr_by_pat('[Ee]mail')
        
        if debug:
            print('first_names:' + str(self.first_names))
            print('emails:' + str(self.emails))

        check_for_blanks(self.first_names)
        check_for_blanks(self.emails)
        assert len(self.first_names) == len(self.emails), \
               "lengthes of first names and emails do not match"
        
    def on_browse(self, event):
        spreadsheet_path = wx_utils.my_file_dialog(parent=None, \
                                                   msg="Chose a spreadsheet file", default_file="", \
                                                   wildcard=spreadsheet_wildcard, \
                                                   kind="open", \
                                                   check_overwrite=False)

        if spreadsheet_path:
            self.spreadsheet_path_box.SetValue(spreadsheet_path)
            self.validate_spreadsheet(spreadsheet_path)
            

    def build_email_text(self, firstname):
        line1 = self.greeting_box.GetValue().encode() % firstname

        body = self.body_box.GetValue().encode()

        closing = self.closing_box.GetValue().encode()

        sig = self.signature_box.GetValue().encode()

        text = line1 + '\n\n' + body + '\n\n' + closing + '\n\n' + \
               sig

        return text


    def build_debug_email_text(self):
        textout = ""

        fmt = '%s: %s\n'
        
        for fname, email in zip(self.first_names, self.emails):
            curline = fmt % (fname, email)
            textout += curline

        return textout
    

    def on_send(self, event):
        print('hello from on_send')

        debug = self.debug_check.GetValue()
        print('debug_check = ' + str(debug))
        
        if debug:
            emails = ['ryanlists@gmail.com']
            first_names = ['Ryan']
        else:
            first_names = self.first_names
            emails = self.emails

        subject = self.subject_box.GetValue().encode()

        N = len(emails)
        n_list = range(N)
        
        for fname, email, n in zip(first_names, emails, n_list):
            print('sending to %s, %i of %i' % (email, n+1, N))
            text = self.build_email_text(fname)
            recipients = [email]
            if debug:
                debug_str = self.build_debug_email_text()
                text += '\n\n' + debug_str
                
            gmail_smtp.send_mail_siue(recipients, subject, text, \
                                      attachmentFilePaths=[])

        
    def OnInit(self):
        """Initialize the :py:class:`MyApp` instance; start by loading
        the xrc resource file and then add other stuff and bind the events"""
        xrcfile = 'multi_email_xrc.xrc'
        self.res = xrc.XmlResource(xrcfile)

        # main frame and panel ---------

        self.frame = self.res.LoadFrame(None,"main_frame")
        self.panel = xrc.XRCCTRL(self.frame,"MainPanel")
        self.browse_button = xrc.XRCCTRL(self.frame,"spreadsheet_browse_button")
        self.send_button = xrc.XRCCTRL(self.frame,"send_button")
        self.spreadsheet_path_box = xrc.XRCCTRL(self.frame,"spreadsheet_path_box")

        self.greeting_box = xrc.XRCCTRL(self.frame,"greeting_box")
        self.body_box = xrc.XRCCTRL(self.frame,"body_box")
        self.closing_box = xrc.XRCCTRL(self.frame,"closing_box")
        self.subject_box = xrc.XRCCTRL(self.frame,"subject_box")
        
        self.signature_box = xrc.XRCCTRL(self.frame,"signature_box")
        self.signature_box.SetValue(mysig)

        self.debug_check = xrc.XRCCTRL(self.frame,"debug_check")
        self.debug_check.SetValue(True)

        ## wx.EVT_BUTTON(self.add_file_button, self.add_file_button.GetId(),
        ##               self.on_add_file)
        ## wx.EVT_BUTTON(self.update_plot_button, self.update_plot_button.GetId(),
        ##               self.on_update_plot)
        ## wx.EVT_BUTTON(self.set_as_fig_button, self.set_as_fig_button.GetId(), \
        ##               self.on_set_as_fig_button)
        ## wx.EVT_BUTTON(self.duplicate_button, self.duplicate_button.GetId(), \
        ##               self.on_duplicate_button)

        ## self.menubar = self.frame.GetMenuBar()
        wx.EVT_BUTTON(self.browse_button, self.browse_button.GetId(),
                      self.on_browse)

        wx.EVT_BUTTON(self.send_button, self.send_button.GetId(),
                      self.on_send)

        self.menubar = self.frame.GetMenuBar()
        self.frame.Bind(wx.EVT_MENU, self.on_exit, \
                        id=xrc.XRCID('quit_menu_item'))

        self.frame.Bind(wx.EVT_MENU, self.save, \
                        id=xrc.XRCID('save_menu_item'))


        self.frame.Bind(wx.EVT_MENU, self.load, \
                id=xrc.XRCID('load_menu_item'))


        ## self.frame.Bind(wx.EVT_BUTTON, self.on_browse, \
        ##                 id=xrc.XRCID('browse_button'))
        ## self.frame.Bind(wx.EVT_MENU, self.on_update_plot, \
        ##                 id=xrc.XRCID('update_plot_menu'))
        ## self.frame.Bind(wx.EVT_MENU, self.on_exit, \
        ##                 id=xrc.XRCID('exit_menu'))
        ## self.frame.Bind(wx.EVT_MENU, self.on_save_current_pd, \
        ##                 id=xrc.XRCID('save_plot_description'))
        ## self.frame.Bind(wx.EVT_MENU, self.on_save_gui_state, \
        ##                 id=xrc.XRCID('save_gui_state'))
        ## self.frame.Bind(wx.EVT_MENU, self.on_save_figure, \
        ##                 id=xrc.XRCID('save_figure'))

        ## figure_menu = wx.Menu()
        ## figure_menu_ids = []
        ## figure_menu_items = []

        ## accelEntries = []


        ## cur_id = wx.NewId()
        ## cur_text = 'Set as Figure'
        ## help_text = 'Set currently selected plots to a Figure #'
        ## cur_item = wx.MenuItem(figure_menu, cur_id, cur_text, help_text)
        ## figure_menu.AppendItem(cur_item)
        ## accelEntries.append((wx.ACCEL_CTRL, ord('F'), cur_id))
        #method_name = 'plot_fig_%i' % j
        #self.Bind(wx.EVT_MENU, self.on_set_as_fig_button, id=cur_id)

        ## self.menubar.Append(self.figure_menu, "Figures")
        ## self.figure_menu_items = figure_menu_items

        ## accelTable  = wx.AcceleratorTable(accelEntries)
        ## self.frame.SetAcceleratorTable(accelTable)



        ## # wx boilerplate
        ## sizer.Add(self.plotpanel, 1, wx.EXPAND)
        ## plot_container.SetSizer(sizer)
        ## #self.plotpanel.SetMinSize((900,600))

        self.frame.SetClientSize((700,700))
        self.frame.Show(1)
        self.SetTopWindow(self.frame)
        return True




if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()




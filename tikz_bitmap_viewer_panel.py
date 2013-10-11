"""This module contains a panel that creates tikz block diagrams from
an xml description of a system.  This block diagrams are converted to
jpegs and place on a static bitmap.

Note that I am using self.parent.blocklist to prevent a toplevel
application from having multiple blocklists for each panel and having
them get out of sync."""

from __future__ import print_function

# Used to guarantee to use at least Wx2.8
#import wxversion
#wxversion.ensureMinimal('2.8')

use_pdfviewer = False

import os, copy, rwkos

#import sys, time, os, gc

import wx
import wx.xrc as xrc

#import wx.grid
#import wx.grid as  gridlib
import numpy as np

import block_diagram_utils
from block_diagram_utils import panel_with_parent_blocklist, change_ext

import xml_utils

xrc_folder = rwkos.FindFullPath('git/wxpython_guis')
#filename = 'tikz_bitmap_viewer_xrc.xrc'
filename = 'tikz_bitmap_viewer_xrc2.xrc'
xrc_path = os.path.join(xrc_folder, filename)

tikz_type_map = {'arbitrary_input':'input', \
                'finite_width_pulse':'input', \
                'step_input':'input', \
                'summing_block':'sum', \
                'swept_sine':'input', \
                }


simple_wire_fmt = '\\draw [->] (%s) -- (%s);'
complex_wire_fmt = '\\draw [->] (%s) %s (%s);'


tikz_header = r"""\input{/Users/rkrauss/git/report_generation/drawing_header}
\def \springlength {2.0cm}
\pgfmathparse{\springlength*3}
\let\damperlength\pgfmathresult
\def \groundX {0.0cm}
\def \groundwidth {4cm}
\def \masswidth {2.5cm}
\pgfmathparse{\masswidth/2}
\let\halfmasswidth\pgfmathresult
\def \wallwidth {0.35cm}
\pgfmathparse{\wallwidth/2}
\let\halfwallwidth\pgfmathresult
\pgfmathparse{\masswidth+0.7cm}
\let\wallheight\pgfmathresult
\def \mylabelshift {0.2cm}

\usetikzlibrary{shapes,arrows}
\tikzstyle{block} = [draw, fill=blue!10, rectangle, 
    minimum height=1.0cm, minimum width=1.0cm]
\tikzstyle{multilineblock} = [draw, fill=blue!10, rectangle, 
    minimum height=1.25cm, minimum width=1.0cm, 
    text width=2cm,text centered,midway]
\tikzstyle{sum} = [draw, fill=blue!20, circle, node distance=1.5cm]
\tikzstyle{input} = [emptynode]%[coordinate]
\tikzstyle{output} = [emptynode]
\tikzstyle{myarrow} = [coordinate, node distance=1.5cm]
\tikzstyle{pinstyle} = [pin edge={to-,thin,black}]
\tikzstyle{serialnode} = [inner sep=0.5mm,rectangle,draw=black, fill=black]
\tikzstyle{serialline} = [draw, ->, ultra thick, densely dashed]
\tikzstyle{mylabel} = [emptynode, yshift=\mylabelshift]

"""


class tikz_panel(wx.Panel, panel_with_parent_blocklist):
    def get_filename(self):
        dirname = ''
        dlg = wx.FileDialog(self.panel, "Choose a file", dirname, \
                            "", "*.xml", wx.OPEN)
        filepath = None
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            filepath = os.path.join(dirname, filename)
            dlg.Destroy()
            return filepath


    def estimate_coordinates(self):
        """Estimate the coordinates of each block.  Assuming that one
        block is set as absolute and all the rest are relative to one
        another, estimate the coordinates of the relative blocks.
        This will be done to try and determine how complicated wires
        should run, i.e. the difference betwee |- and -| in tikz
        (first up or down, then over or vice versa).

        Note that you must call block.set_params_as_attrs() for each
        block in self.parent.blocklist before calling this method."""
        #first, find the abs block and make sure there is only one
        abs_inds = self.find_abs_blocks()
        assert len(abs_inds) > 0, "did not find any absolute blocks in self.parent.blocklist"
        assert len(abs_inds) == 1, "found more than one absolute blocks in self.parent.blocklist"

        #I want to be able to undo this if I need to
        backup_list = copy.copy(self.parent.blocklist)


        abs_block = self.parent.blocklist.pop(abs_inds[0])
        sorted_blocks = [abs_block]

        relative_list = [block.params['relative_block'] for block in self.parent.blocklist]

        #now,how to do the sortin?
        #
        # - each block can only have one relative block, so it shouldn't be too bad

        # for each item in sorted_blocks, search for any block that is
        # relative to it and add that block to the list

        i = 0

        while i < len(sorted_blocks):
            curname = sorted_blocks[i].name
            try:
                next_index = relative_list.index(curname)
                relative_list.pop(next_index)
                curblock = self.parent.blocklist.pop(next_index)
                sorted_blocks.append(curblock)
            except ValueError:
                i += 1


        if len(self.parent.blocklist) > 0:
            #sorting failed
            self.parent.blocklist = backup_list
            print('sorting failed')
            return
        else:
            #blocks are correctly sorted
            self.parent.blocklist = sorted_blocks
            #!#!#: sort the blocks in the list box here
            #self.sort_list_box()


        for block in self.parent.blocklist:
            #block.set_params_as_attrs()#<--- this should be done before calling this method
            if block.params['position_type'] == 'absolute':
                coords_str = block.params['abs_coordinates']
                coords_str_list = coords_str.split(',')
                coords_str_list = [item.strip() for item in coords_str_list]
                coords = [float(item) for item in coords_str_list]
                assert len(coords) == 2, "Problem with abs coords: %s" % coords_str
                block.coordinates = np.array(coords)
            else:
                rel_name = block.params['relative_block']
                rel_block = self.find_block(rel_name)
                rel_distance = float(block.params['relative_distance'])
                direction = block.params['relative_direction']
                dir_dict = {'right of':np.array([1.0,0]), \
                            'left of':np.array([-1.0,0]), \
                            'above of':np.array([0.0,1.0]), \
                            'below of':np.array([0.0,-1.0]), \
                            }
                shift = rel_distance*dir_dict[direction]
                if hasattr(block, 'xshift') and block.xshift:
                    shift += np.array([block.xshift,0])
                if hasattr(block, 'yshift') and block.yshift:
                    shift += np.array([0,block.yshift])

                block.coordinates = rel_block.coordinates + shift

            print('block name: %s' % block.name)
            print('   coordinates: ' + str(block.coordinates))


    def create_tikz_block_lines(self):
        mylist = []
        abs_node_pat = '\\node [%s] (%s) at (%s) {%s};'#type, name, coordinates, label
        rel_opt_pat = '%s, %s=%s, node distance=%scm'
        rel_node_pat = '\\node [%s] (%s) {%s};'#type, relative direction, relative block, \
            #node distance, name, label

        for block in self.parent.blocklist:
            blocktype = block.blocktype
            label = block.params['label']
            print('label = ' +str(label))
            if label is None:
                label = ''
            print('label = ' +str(label))                    
            if tikz_type_map.has_key(blocktype):
                tikz_type = tikz_type_map[blocktype]
            else:
                tikz_type = 'block'#generic block
            if block.params['position_type'] == 'absolute':
                mytup = (tikz_type, block.name, block.params['abs_coordinates'], label)
                blockline = abs_node_pat % mytup
            elif block.params['position_type'] == 'relative':
                opt_tup = (tikz_type, block.params['relative_direction'], \
                           block.params['relative_block'], \
                           block.params['relative_distance'])
                opt_str = rel_opt_pat % opt_tup
                if block.params.has_key('tikz_block_options') and block.params['tikz_block_options']:
                    opt_str += ', ' + block.params['tikz_block_options']
                if hasattr(block, 'xshift') and block.xshift:
                    xshift_str = ', xshift=%0.4gcm' % block.xshift
                    opt_str += xshift_str
                if hasattr(block, 'yshift') and block.yshift:
                    yshift_str = ', yshift=%0.4gcm' % block.yshift
                    opt_str += yshift_str

                mytup = (opt_str, block.name, label)
                blockline = rel_node_pat % mytup
            mylist.append(blockline)
            if block.blocktype == 'summing_block':
                sign_label0 = block.name + '_label0'
                sign_label1 = block.name + '_label1'
                line0 = r'\path (%s) ++(-55:0.4) node (%s) {\small{$-$}};' % \
                        (block.name, sign_label0)
                line1 = r'\path (%s) ++(155:0.4) node (%s) {\small{$+$}};' % \
                        (block.name, sign_label1)
                mylist.append(line0)
                mylist.append(line1)


        return mylist



    def create_output_lines(self):
        mylines = ['%output lines/arrows']
        out = mylines.append

        for block in self.parent.blocklist:
            if block.params.has_key('show_outputs'):
                show_outputs = block.params['show_outputs']
                if type(show_outputs) == str:
                    show_outputs = xml_utils.str_to_bool(show_outputs)

                if show_outputs:
                    output_nodes = []
                    # define the output node near the block
                    # define the output node iteself (eventually need to care about direction, I think)
                    #  ? can I get direction out of output angle ?
                    # define the arrow tip node if necessary
                    # draw the output line
                    # draw the output arrow
                    # add the label if given

                    #\node [output] at (serial_plant.-30) (output0) {};
                    basename = block.name
                    num_outputs = block.get_num_outputs()

                    startline = '\\node [output] at (%s.%0.4g) (%s) {};'
                    outline = '\\node [emptynode, %s=%s, node distance=%0.4gcm] (%s) {};'
                    arrowline = '\\draw [->] (%s) -- (%s);'
                    nonarrowline = '\\draw [-] (%s) -- (%s);'
                    labelline = '\\node [mylabel, above of=%s, node distance=0cm] (%s) {%s};'


                    #\node [myarrow, right of=output0, emptynode, node distance=1cm] (serial_plant_out0) {};
                    for i in range(num_outputs):
                        startname = basename + '_out%i_start' % i
                        curangle = float(block.params['output_angles'][i])
                        outputname = basename + '_out%i' % i
                        out(startline % (basename, curangle, startname))
                        if abs(curangle) < 95.0 or curangle > 265.0:
                            direction = 'right of'
                        else:
                            direction = 'left of'

                        curdistance = float(block.params['output_distances'][i])
                        out(outline % (direction, startname, curdistance, outputname))

                        show_arrow = xml_utils.str_to_bool(block.params['show_output_arrows'][i])
                        if show_arrow:
                            arrowname = basename + '_out%i_arrow' % i
                            arrowdist = 0.7# bad, bad hard coding
                            out(outline % (direction, outputname, arrowdist, arrowname))
                            out(arrowline % (startname, arrowname))
                        else:
                            out(nonarrowline % (startname, outputname))

                        curlabel = block.params['output_labels'][i]
                        if curlabel:
                            labelname = basename + '_out%i_label' % i
                            out(labelline % (outputname, labelname, curlabel))

                        output_nodes.append(outputname)

                    block.output_nodes = output_nodes

        return mylines



    def find_input_node(self, block, attr='input'):
        input_ind = 0
        if block.params.has_key('input_ind') and block.params['input_ind']:
            input_ind = int(block.params['input_ind'])

        input_block = self.find_block(block.params[attr])
        if hasattr(input_block, 'output_nodes'):
            in_node = input_block.output_nodes[input_ind]
        else:
            in_node = input_block.name
        return in_node


    def additional_input_wire(self, block, attr='input2'):
        # bookmark: I will need to allow input_ind to be used here at
        # some point
        input_block = self.find_block(block.params[attr])
        if input_block:
            in_node = self.find_input_node(block, attr=attr)

            input_x, input_y = input_block.coordinates
            my_x, my_y = block.coordinates

            wire_line = None

            if (my_x == input_x) or (my_y == input_y):
                wire_fmt = '--'
            elif my_x < input_x:
                #I am to the left of my input
                if my_y < input_y:
                    wire_fmt = '|-'#vertical first, then horizontal
                else:
                    wire_fmt = '-|'#horizontal first, then, vertical
            else:
                #I am to the right of my input
                wire_fmt = '|-'

            wire_line = complex_wire_fmt % (in_node, wire_fmt, block.name)
            return wire_line


    def update_latex(self, tex_path):
        mylist = [r'\begin{document}', \
                  r"\begin{tikzpicture}[every node/.style={font=\large}, node distance=2.5cm,>=latex']", \
                  ]

        for block in self.parent.blocklist:
            block.set_params_as_attrs()

        #estimate block coordinates for tricky wires and to get the
        #blocks to ouput in a valid order so all the relative
        #references work
        self.estimate_coordinates()

        #draw blocks
        block_list_tikz = self.create_tikz_block_lines()
        mylist.extend(block_list_tikz)

        #draw outputs
        output_lines = self.create_output_lines()
        mylist.extend(output_lines)


        # Draw wires
        #
        # This will be fairly complicated.
        #
        # Here is example code from a simple file (DC_motor_kp.tex)
        #
        ## \draw [->] (input) -- (sum) node[pos=0.9, yshift=0.25cm] {\small{$+$}};
        ## \draw [->] (sum) -- (controller);
        ## \draw [->] (controller) -- (plant);
        ## \draw [->] (plant) -- (output) node [emptynode] (outarrow) [pos=0.5] {};

        ## \coordinate [below of=plant, node distance=1.5cm] (tmp);
        ## \draw [->] (outarrow) |- (tmp) -| (sum) node[pos=0.9, xshift=0.2cm] {{\small $-$}};

        # draw wires
        mylist.append('')
        mylist.append('% wires')


        first = 1
        for block in self.parent.blocklist:
            if block.params.has_key('input') and block.params['input']:
                #the block has an input and should get some kind of wire
                in_node = self.find_input_node(block)
                wire_line = None
                if (block.params['position_type'] == 'relative') and \
                       block.params['input'] == block.params['relative_block']:
                    if hasattr(block,'xshift') and block.xshift:
                        #this is not a simple wire
                        wire_line = None
                    else:
                        #this is a simple wire
                        wire_line = simple_wire_fmt % (in_node, block.name)
                if wire_line is None:
                    #this is a more complicate wire
                    input_block = self.find_block(block.params['input'])
                    input_x, input_y = input_block.coordinates
                    my_x, my_y = block.coordinates
                    if my_x < input_x:
                        #I am to the left of my input
                        if my_y < input_y:
                            wire_fmt = '|-'#vertical first, then horizontal
                        else:
                            wire_fmt = '-|'#horizontal first, then, vertical
                    else:
                        #I am to the right of my input
                        wire_fmt = '|-'

                    wire_line = complex_wire_fmt % (in_node, wire_fmt, block.name)

                if wire_line:
                    mylist.append(wire_line)


                if hasattr(block, 'input2'):
                    wire_line2 = self.additional_input_wire(block, attr='input2')
                    if wire_line2:
                        mylist.append(wire_line2)


        # additional wires for summing blocks

        mylist.append('\\end{tikzpicture}')
        mylist.append('\\end{document}')
        list_str = '\n'.join(mylist)
        full_str = tikz_header + '\n' + list_str
        f = open(tex_path, 'wb')
        f.writelines(full_str)
        f.close()
        ## \node (input) {$\theta_d$};
        ## \node [sum, right of=input] (sum) {};
        return mylist


    def on_save_tikz(self, event=0):
        ## mylist = tikz_header.split('\n')#<-- is this good or bad?
        ##                                 #should I create my list first
        ##                                 #and then convert it to a
        ##                                 #string?
        tex_path = wx_utils.my_file_dialog(parent=self.frame, \
                                           msg="Save TiKZ Block Diagram drawing as", \
                                           kind="save", \
                                           wildcard=tex_wildcard, \
                                           )
        if tex_path:
            self.update_latex(tex_path)
        return tex_path


    def on_update_diagram(self, event=0):
        #w, h = self.static_bitmap.Size
        #print('bitmap size: %s, %s' % (w,h))
        wp, hp = self.Size

        if hasattr(self, 'tex_path'):
            tex_path = self.tex_path
        elif hasattr(self, 'xml_path'):
            tex_path = change_ext(self.xml_path, 'tex')
            self.tex_path = tex_path
        else:
            tex_path = self.on_save_tikz(event)

        if tex_path:
            self.update_latex(tex_path)

            cmd = 'pdflatex %s' % tex_path
            os.system(cmd)

            if use_pdfviewer:
                pdfpath = change_ext(tex_path, '.pdf')
                self.pdfviewer.LoadFile(pdfpath)

            else:
                curdir = os.getcwd()
                dir, fn = os.path.split(tex_path)
                fno, ext = os.path.splitext(fn)
                pdfname = fno + '.pdf'

                os.chdir(dir)
                cmd2 = 'pdf_to_jpeg_one_page.py -r 600 %s' % pdfname
                os.system(cmd2)

                jpgname = fno + '.jpg'

                smaller_jpegname = fno + '_smaller.jpg'
                jpgpath = os.path.join(dir, smaller_jpegname)

                #imagemajick resize
                cmd = 'convert ' + jpgname + \
                      ' -filter Cubic -resize 50% -unsharp 0x0.75+0.75+0.008 ' + \
                      smaller_jpegname
                os.system(cmd)

                Img = wx.Image(jpgpath, wx.BITMAP_TYPE_JPEG)
                wi, hi = Img.GetSize()

                if (wi > wp) or (hi > hp):
                    ratio_w = wp/float(wi)
                    ratio_h = hp/float(hi)
                    if ratio_w < ratio_h:
                        #width needs more shrinking
                        scale = ratio_w
                    else:
                        scale = ratio_h
                    #override scale for now; then use the menu based override option
                    ## scale = ratio_w
                    ## if hasattr(self, 'diagram_scaling'):
                    ##     if self.diagram_scaling.lower() == 'height':
                    ##         print('in scale, ratio_h = %0.4g' % ratio_h)
                    ##         scale = ratio_h
                    ##     else:
                    ##         scale = ratio_w
                    new_w = int(wi*scale)
                    new_h = int(hi*scale)
                    #Img = Img.Scale(new_w, new_h)#<-- this works but is ugly
                    scaled_jpegname = fno + '_scaled.jpg'
                    scaled_path = os.path.join(dir, scaled_jpegname)
                    size_str = '%ix%i' % (new_w, new_h)
                    cmd = 'convert ' + jpgname + ' -filter Cubic -resize ' + size_str + \
                          ' -unsharp 0x0.75+0.75+0.008 ' + scaled_jpegname
                    os.system(cmd)

                    #Img = wx.Image(smaller_jpegname, wx.BITMAP_TYPE_JPEG)
                    Img = wx.Image(scaled_path, wx.BITMAP_TYPE_JPEG)


                self.static_bitmap.SetBitmap(wx.BitmapFromImage(Img))
                os.chdir(curdir)

            self.Refresh()


    def on_load_xml(self, event):
        xml_path = panel_with_parent_blocklist.on_load_xml(self, event)
        if xml_path:
            self.on_update_diagram(event)
        

    ## def on_update_diagram_button(self, event=0):
    ##     print('in on_update_diagram_button')
    ##     self.on_update_diagram(event)
            

    def __init__(self, parent):
        pre = wx.PrePanel()
        res = xrc.XmlResource(xrc_path)
        res.LoadOnPanel(pre, parent, "tikz_viewer_panel") 
        self.PostCreate(pre)
        self.parent = parent
        ## self.Bind(wx.EVT_BUTTON, self.on_update_diagram, \
        ##           xrc.XRCCTRL(self, "update_diagram_button")) 
        self.static_bitmap = xrc.XRCCTRL(self, "static_bitmap")
        assert hasattr(self.parent, 'blocklist'), \
               "The parent of a tikz_viewer_panel must have a blocklist attribute."

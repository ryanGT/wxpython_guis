import os
from block_diagram_xml import bd_XML_element, block_diagram_system_parser
import wx_utils

xml_wildcard = "XML files (*.xml)|*.xml"
tex_wildcard = "TEX files (*.tex)|*.tex"


def change_ext(pathin, new_ext):
    pne, ext = os.path.splitext(pathin)
    if new_ext[0] != '.':
        new_ext = '.' + new_ext
    newpath = pne + new_ext
    return newpath


class panel_with_parent_blocklist(object):
    """This is designed to be a mixin class for any part of a block
    diagram system that would have a blocklist parameter, such as a
    tikz viewer or a block parameters viewer/editor panel.  This gets
    tricky if different modular panels will each need access to the
    blocklist, so I am forcing the element to use
    self.bd_parent.blocklist.  This will be slightly tricky, but will
    prevent modifying one panels blocklist and the others not getting
    modified."""
    def find_abs_blocks(self):
        abs_inds = []

        for i, block in enumerate(self.bd_parent.blocklist):
            if block.params['position_type'] == 'absolute':
                abs_inds.append(i)

        return abs_inds


    def find_block(self, block_name):
        for block in self.bd_parent.blocklist:
            if block.name == block_name:
                return block


    def append_one_block(self, name, blocktype, params_dict):
        new_block = bd_XML_element(name=name, \
                                   blocktype=blocktype, \
                                   params=params_dict)
        self.bd_parent.blocklist.append(new_block)


    def on_load_xml(self, event=0):
        """Load a list of blocks from a block diagram xml file"""
        xml_path = wx_utils.my_file_dialog(parent=self, \
                                           msg="Load block list/system from XML", \
                                           kind="open", \
                                           wildcard=xml_wildcard, \
                                           )
        if xml_path:
            print('xml_path = ' + xml_path)
            myparser = block_diagram_system_parser(xml_path)
            myparser.parse()
            myparser.convert()
            self.bd_parent.blocklist = []
            for block in myparser.block_list:
                print('block.params = %s' % block.params)
                self.append_one_block(block.name, block.blocktype, block.params)

            self.xml_path = xml_path

            return self.xml_path

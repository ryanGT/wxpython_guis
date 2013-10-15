max_rows_default = 20

class panel_with_params_grid(wx.Panel):
    """This is a base class for a panel that contains a wx.Grid
    specifically called self.params_grid that is used to basically
    display and interact with a dictionary."""
    def clear_params_grid(self):
        self.params_grid.SetCellValue(0,0, "parameter")
        self.params_grid.SetCellValue(0,1, "value")
        for i in range(1,max_rows):
            self.params_grid.SetCellValue(i,0, "")
            self.params_grid.SetCellValue(i,1, "")


    def set_max_rows(self, max_rows):
        self.max_rows = max_rows


    def _get_max_rows(self):
        if hasattr(self, 'max_rows'):
            return self.max_rows
        else:
            return max_rows_default

    def build_params_dict(self):
        params_dict = {}
        exit_code = 0
        max_rows = self._get_max_rows()
        for i in range(1,max_rows):
            key = self.params_grid.GetCellValue(i,0)
            val = self.params_grid.GetCellValue(i,1)
            key = key.strip()
            val = val.strip()
            val = xml_utils.full_clean(val)
            if not key:
                break
            elif not val:
                ## msg = 'Empty parameters are not allow: %s' % key
                ## wx.MessageBox(msg, 'Parameter Error', 
                ##               wx.OK | wx.ICON_ERROR)
                ## exit_code = 1
                ## break
                val = None#do I really want to make this explicit, or
                    #just leave it blank?
            params_dict[key] = val
        print('params_dict = %s' % params_dict)
        return params_dict

    
    def set_grid_val(self, prop, value):
        i = 0
        max_rows = self._get_max_rows()
        while i < max_rows:
            attr = self.params_grid.GetCellValue(i, 0)
            if attr == prop:
                self.params_grid.SetCellValue(i, 1, str(value))
                return
            else:
                i += 1


    def delete_grid_rows(self, prop_list):
        i = 0
        max_rows = self._get_max_rows()
        while i < max_rows:
            prop = self.params_grid.GetCellValue(i, 0)
            if prop in prop_list:
                self.params_grid.DeleteRows(i, 1)
            else:
                i += 1


    def find_first_empty_row(self):
        i = 0
        max_rows = self._get_max_rows()
        while i < max_rows:
            prop = self.params_grid.GetCellValue(i, 0)
            if not prop:
                return i
            else:
                i += 1


    def set_cell_append_if_necessary(self, row, col=0, val=''):
        n_rows = self.params_grid.GetNumberRows()
        if row >= n_rows:
            self.params_grid.AppendRows(1)
            row = self.find_first_empty_row()
        self.params_grid.SetCellValue(row, col, val)


    def append_rows(self, prop_list):
        print('in append_rows')
        print('prop_list = ' + str(prop_list))
        start_ind = self.find_first_empty_row()
        print('start_ind = ' + str(start_ind))
        for i, prop in enumerate(prop_list):
            self.set_cell_append_if_necessary(i+start_ind, 0, prop)


    def get_existing_props(self):
        prop_list = []
        max_rows = self._get_max_rows()
        for i in range(1, max_rows):
            prop = self.params_grid.GetCellValue(i, 0)
            if prop:
                prop_list.append(prop)
            else:
                return prop_list


    def append_rows_if_missing(self, prop_list):
        existing_rows = self.get_existing_props()
        new_items = [item for item in prop_list if item not in existing_rows]
        self.append_rows(new_items)


    def autosize_columns(self, event=0):
        self.params_grid.AutoSizeColumns()


    def get_grid_val(self, prop):
        i = 0
        max_rows = self._get_max_rows()
        while i < max_rows:
            attr = self.params_grid.GetCellValue(i, 0)
            if attr == prop:
                val = self.params_grid.GetCellValue(i, 1)
                return val.strip()
            else:
                i += 1



    def display_params(self, params_dict, filt_func=None):
        self.clear_params_grid()
        keys = params_dict.keys()
        keys.sort()
        if filt_func is None:
            filt_keys = keys
        else:
            filt_keys = filter(filt_func, keys)

        for i, key in enumerate(filt_keys):
            self.params_grid.SetCellValue(i+1,0, key)
            val = params_dict[key]
            if val is None:
                val = ''
            if type(val) not in [str, unicode]:
                val = str(val)
            self.params_grid.SetCellValue(i+1,1, val)



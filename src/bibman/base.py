import curses


class ScrollableList(object):
    DEFAULT_COLOR = 1
    HIGHLIGHT_COLOR = 2
    HIGHLIGHT_COLOR2 = 3
    def __init__(self, pos, items, visible_off_focus=False, is_on_focus=True, wrap=False):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        # self.begin_line = begin_line
        # self.begin_col = begin_col
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)
        self.win.bkgd(curses.color_pair(ScrollableList.DEFAULT_COLOR))
        self.secondary_chosen_ind = 0 # the item will be underline when focus is lost
        self.is_on_focus = is_on_focus # whether to highligh the current selected item

        # whether to underline the `secondary_chosen_ind` when focus is lost
        self.visible_off_focus = visible_off_focus

        self.items = items
        self.start_index = 0
        self.offset = 3
        self.channels = dict()
        self.__crossed_inds = []
        self._offset_prefix = 0

        # A single chosen item, shown in a white bold background
        self.__chosen_ind = 0

        # A list of multiple chosen items, shown in a yellow bold background
        self.__mult_chosen_inds = []

    def render(self):
        def cut_short(item):
            lines = item.split('\n')
            new_lines = []
            for line in lines:
                line = line[self._offset_prefix:]
                if len(line) > self.ncols-4:
                    line = line[:self.ncols-6] +' ...'
                new_lines.append(line)
            new_item = '\n'.join(new_lines)
            return new_item

        self.win.erase()
        visible_start = self.start_index
        visible_end = self.start_index+self.nlines-1
        if self.__chosen_ind > visible_start+self.offset-1 and self.__chosen_ind < visible_end-self.offset:
            pass
        else:
            if self.__chosen_ind<=visible_start+self.offset:
                self.start_index = max(0, self.__chosen_ind-self.offset+1)
            else:
                self.start_index = max(0, self.__chosen_ind+self.offset - self.nlines+1)

        current_line = 1
        for i in range(0, min(self.nlines-1, len(self.items) -self.start_index)):
            item = self.items[i+self.start_index]
            item = cut_short(item)
            if i == self.__chosen_ind-self.start_index and self.is_on_focus:
                self.win.addstr(current_line, 1, item, curses.A_STANDOUT)
            elif (i+self.start_index) in self.__crossed_inds:
                self.win.addstr(current_line, 1, item, curses.A_DIM)
            elif i == self.secondary_chosen_ind-self.start_index and self.visible_off_focus:
                self.win.addstr(current_line, 1, item, curses.A_UNDERLINE)
            elif (i+self.start_index) in self.__mult_chosen_inds:
                self.win.addstr(current_line, 1, item, curses.A_STANDOUT | curses.color_pair(ScrollableList.HIGHLIGHT_COLOR))
            else:
                self.win.addstr(current_line, 1, item)
            tmp = max(len(item.split('\n')),1)
            current_line += tmp
        self.win.box()
        self.win.refresh()

    def select_next(self):
        if self.__chosen_ind < len(self.items)-1:
            self.__chosen_ind += 1
            self.render()

    def broadcast(self, event, channel):
        for listener in self.channels[channel]:
            listener.receive_event(event)

    def receive_event(self, event):
        pass

    def select_previous(self):
        if self.__chosen_ind > 0:
            self.__chosen_ind -= 1
            self.render()

    def get_focus(self):
        self.is_on_focus = True
        self.render()

    def get_single_chosen_item(self):
        return self.__chosen_ind

    def get_active_inds(self):
        if len(self.__mult_chosen_inds)>0:
            return self.__mult_chosen_inds
        else:
            return [self.__chosen_ind]

    def select(self):
        self.__mult_chosen_inds.append(self.__chosen_ind)

    def deselect(self):
        if self.__chosen_ind in self.__mult_chosen_inds:
            self.__mult_chosen_inds.remove(self.__chosen_ind)

    def toggle_select(self):
        if self.__chosen_ind in self.__mult_chosen_inds:
            self.deselect()
        else:
            self.select()
        self.select_next()

    def lost_focus(self):
        self.is_on_focus = False
        self.render()

    def goto(self, line_number):
        # Just a trick to make to move appears consistent
        # Move to the end first
        self.__chosen_ind = len(self.items)-1
        self.render()

        if line_number!=-1:
            self.__chosen_ind = line_number
            self.render()

    def update(self, items, chosen_ind=0, start_index=0, secondary_chosen_ind=0, disable_inds=[]):
        self.items = items
        # todo a very naive attempt to prevent exception
        self.__chosen_ind = min(chosen_ind, len(items)-1)

        # todo a very naive attempt to prevent exception
        self.start_index = min(start_index, len(items)-1)

        # todo a very naive attempt to prevent exception
        self.secondary_chosen_ind = min(secondary_chosen_ind, len(items)-1)
        self.__crossed_inds = disable_inds

        self.__mult_chosen_inds = []

        self.render()

    def resize(self, nlines, ncols):
        self.clear_gui()
        self.win.resize(nlines, ncols)
        self.nlines = nlines
        self.ncols = ncols
        self.render()

    def move(self, y, x):
        self.clear_gui()
        self.win.mvwin(y, x)
        self.render()

    def clear_gui(self):
        self.win.border(' ', ' ', ' ',' ',' ',' ',' ',' ')
        self.win.refresh()
        self.win.clear()
        self.win.refresh()

    def add_listener(self, listener, channel):
        if channel in self.channels:
            self.channels[channel].append(listener)
        else:
            self.channels[channel] = [listener]

    def listen_to(self, host, channel):
        host.add_listener(self, channel)

    def dump(self):
        data = {'__chosen_ind': self.__chosen_ind, 'size': (self.nlines, self.ncols), \
                'items': self.items, 'start_index': self.start_index, \
                'offset': self.offset, 'channels': self.channels}
        return data

    def recover(self, data):
        self.win.bkgd(curses.color_pair(ScrollableList.DEFAULT_COLOR))
        self.__chosen_ind = data['__chosen_ind']
        self.nlines = data['size'][0]
        self.ncols = data['size'][1]
        self.items = data['items']
        self.start_index = data['start_index']
        self.offset = data['offset']
        self.channels = data['channels']
        self.render() # todo maybe?

    def shift_right(self, step=1):
        self._offset_prefix += 1
        self.render()

    def shift_left(self, step=1):
        if self._offset_prefix > 0:
            self._offset_prefix -= 1
            self.render()

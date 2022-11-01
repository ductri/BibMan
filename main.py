import curses
from curses import wrapper
import random
import subprocess
import os
from curses.textpad import Textbox
import math

from anytree import Node


from utils.data_manager import DatabaseManager


def print_me(screen, msg, ncol=0):
    screen.addstr(0, ncol, msg) # divide by zero


class ScrollableList(object):
    def __init__(self, pos, items, visible_off_focus=False, is_on_focus=True):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        # self.begin_line = begin_line
        # self.begin_col = begin_col
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)
        self.chosen_ind = 0
        self.secondary_chosen_ind = 0 # the item will be underline when focus is lost
        self.is_on_focus = is_on_focus # whether to highligh the current selected item
        self.visible_off_focus = visible_off_focus # whether to underline the `secondary_chosen_ind` when focus is lost
        self.items = items
        self.start_index = 0
        self.offset = 3
        """
        Got to implement such that we only care about chosen index, the visiable window should react accordingly.
        """

    def render(self):
        self.win.erase()
        visible_start = self.start_index
        visible_end = self.start_index+self.nlines-1
        if self.chosen_ind > visible_start+self.offset-1 and self.chosen_ind < visible_end-self.offset:
            pass
        else:
            if self.chosen_ind<=visible_start+self.offset:
                self.start_index = max(0, self.chosen_ind-self.offset+1)
            else:
                self.start_index = max(0, self.chosen_ind+self.offset - self.nlines+1)

        for i in range(0, min(self.nlines-1, len(self.items) -self.start_index)):
            item = self.items[i+self.start_index]
            if len(item) > self.ncols-1:
                item = item[:self.ncols-6] +' ...'

            if i == self.chosen_ind-self.start_index and self.is_on_focus:
                    self.win.addstr(i+1, 1, item, curses.A_STANDOUT)
            elif i == self.secondary_chosen_ind-self.start_index and self.visible_off_focus:
                    self.win.addstr(i+1, 1, item, curses.A_UNDERLINE)
            else:
                self.win.addstr(i+1, 1, item)

        self.win.box()
        self.win.refresh()

    def select_next(self):
        if self.chosen_ind < len(self.items)-1:
            self.chosen_ind += 1
            self.render()

    def select_previous(self):
        if self.chosen_ind > 0:
            self.chosen_ind -= 1
            self.render()

    def get_focus(self):
        self.is_on_focus = True
        self.render()

    def lost_focus(self):
        self.is_on_focus = False
        self.render()

    def goto(self, line_number):
        # Just a trick to make to move appears consistent
        # Move to the end first
        self.chosen_ind = len(self.items)-1
        self.render()

        if line_number!=-1:
            self.chosen_ind = line_number
            self.render()

    def update(self, items, chosen_ind=0, start_index=0):
        self.items = items
        self.chosen_ind = chosen_ind
        self.start_index = start_index
        self.render()

    def resize(self, nlines, ncols):
        self.clear()
        self.win.resize(nlines, ncols)
        self.nlines = nlines
        self.ncols = ncols
        self.render()

    def move(self, y, x):
        self.clear()
        self.win.mvwin(y, x)
        self.render()

    def clear(self):
        self.win.border(' ', ' ', ' ',' ',' ',' ',' ',' ')
        self.win.refresh()
        self.win.clear()
        self.win.refresh()

class TreeList(object):
    def __init__(self, pos, mdict, is_on_focus=False, default_tag_name='default'):
        """
        This class does too much business than it should!
        """

        def construct_tree(parent, mdict):
            for k, v in mdict.items():
                node = Node(k, parent=parent, expanded=False)
                construct_tree(node, v)
        nlines, ncols, begin_line, begin_col = pos
        self.mdict = mdict
        self.tree = Node(default_tag_name, expanded=True)
        construct_tree(self.tree, mdict)
        self.flatten_nodes = TreeList.render_tree(self.tree)
        self.main_list = ScrollableList((nlines, ncols, begin_line, begin_col), [item.name for item  in self.flatten_nodes], visible_off_focus=False, is_on_focus=is_on_focus)
        self.main_list.secondary_chosen_ind = self.main_list.chosen_ind

    def render(self):
        self.main_list.render()

    def select_next(self):
        self.main_list.select_next()

    def select_previous(self):
        self.main_list.select_previous()

    def get_focus(self):
        self.main_list.get_focus()

    def lost_focus(self):
        self.main_list.lost_focus()

    def goto(self, line_number):
        self.main_list.goto(line_number)

    def expand(self):
        chosen_node = self.flatten_nodes[self.main_list.chosen_ind]
        chosen_node.expanded = True
        self.flatten_nodes = TreeList.render_tree(self.tree)
        self.main_list.update([' '*(node.depth-1)*2 + node.name for node in self.flatten_nodes], chosen_ind=self.main_list.chosen_ind, start_index=self.main_list.start_index)

    def collapse(self):
        chosen_node = self.flatten_nodes[self.main_list.chosen_ind]
        chosen_node.parent.expanded=False
        self.flatten_nodes = TreeList.render_tree(self.tree)
        self.main_list.update([' '*(node.depth-1)*2 + node.name for node in self.flatten_nodes], chosen_ind=self.flatten_nodes.index(chosen_node.parent), start_index=self.main_list.start_index)

    def render_tree(root):
        flatten_nodes = []
        for node in root.children:
            flatten_nodes.append(node)
            if node.expanded:
                flatten_nodes.extend(TreeList.render_tree(node))
        return flatten_nodes

    def get_tags(self):
        return set(self.flatten_nodes[self.main_list.chosen_ind].path[-1].name.split('/'))

    def update_current_item(self):
        self.main_list.secondary_chosen_ind = self.main_list.chosen_ind
        self.render()

    def resize(self, nlines, ncols):
        self.main_list.resize(nlines, ncols)

    def move(self, y, x):
        self.main_list.move(y, x)

    def update(self, items, chosen_ind=0, start_index=0):
        pass

class Status(object):
    def __init__(self, pos):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)

    def render(self, msg):
        self.win.erase()
        if len(msg) > self.ncols:
            msg = msg[:self.ncols-6] +' ...'
        self.win.addstr(0, 1, msg)
        self.win.refresh()

    def clear(self):
        self.win.erase()
        self.win.refresh()

class MyInput(object):
    def __init__(self, pos):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)
        self.box = Textbox(self.win)

    def active(self):
        curses.curs_set(True)
        self.box.edit()
        self.msg = self.box.gather()
        curses.curs_set(False)
        self.win.erase()
        # self.win.refresh()

    def get(self):
        return self.msg

class MainApp(object):
    def __init__(self, stdscr):
        self.database = DatabaseManager()
        self.stdscr = stdscr
        self.nlines, self.ncols = self.stdscr.getmaxyx()

        self.layout_ratio = (0.1, 0.6, 0.3)
        self.padding = 3

        self.tree_pos, self.col1_pos, self.col2_pos, self.status_pos, _ = self.__estimate_layout()

    def __estimate_layout(self, is_tree_visible=True):
        nlines, ncols = self.stdscr.getmaxyx()
        is_enlarging = False
        if ncols > self.ncols:
            is_enlarging = True
        self.nlines = nlines
        self.ncols = ncols

        if is_tree_visible:
            self.layout_ratio = (0.1, 0.6, 0.3)
        else:
            self.layout_ratio = (0.0, 0.6, 0.3)
        list_ncols = [math.floor(self.layout_ratio[0]*ncols), math.floor(self.layout_ratio[1]*ncols)]
        list_ncols.append(ncols - list_ncols[0] - list_ncols[1]-2*self.padding-2)
        tree_pos = (10, list_ncols[0], 1, 1) # (nlines, ncols, begin_line, begin_col)
        col1_pos = (10, list_ncols[1], 1, 1+list_ncols[0]+self.padding) # (nlines, ncols, begin_line, begin_col)
        col2_pos = (10, list_ncols[2], 1, 1+list_ncols[0] + self.padding+list_ncols[1]+self.padding) # (nlines, ncols, begin_line, begin_col)
        status_pos = (1, ncols, nlines-1, 1)

        return tree_pos, col1_pos, col2_pos, status_pos, is_enlarging

    def run(self):
        stdscr = self.stdscr
        curses.curs_set(False)
        stdscr.clear()
        stdscr.refresh()

        collection_tree = self.database.get_collection()
        first_collection = list(collection_tree.keys())[0]
        self.papers = self.database.get_list_papers([first_collection])
        tree = TreeList(self.tree_pos, collection_tree)
        tree.render()

        list_items_1 = [paper['title'] for paper in self.papers]
        my_list1 = ScrollableList(self.col1_pos, list_items_1, is_on_focus=True)
        my_list1.render()

        if len(self.papers) > 0:
            attributes = MainApp.get_paper_attributes(self.papers[my_list1.chosen_ind])
        else:
            attributes = []
        my_list2 = ScrollableList(self.col2_pos, attributes, is_on_focus=False, visible_off_focus=False)
        my_list2.render()

        my_cols = [tree, my_list1, my_list2]
        status_bar = Status(self.status_pos)
        editwin = curses.newwin(5,30, 2,1)
        input_box = MyInput(self.status_pos)
        is_tree_visible = True

        chosen_col = 1
        my_cols[chosen_col].get_focus()
        tmp = 0
        while True:
            c = status_bar.win.getch()
            if c == ord('q'):
                break
            elif c == ord('j'):
                my_cols[chosen_col].select_next()
                if chosen_col == 1:
                    chosen_ind = my_cols[chosen_col].chosen_ind
                    if len(self.papers)>0:
                        attributes = MainApp.get_paper_attributes(self.papers[chosen_ind])
                        my_cols[2].update(attributes, chosen_ind=0, start_index=0)
            elif c == ord('k'):
                my_cols[chosen_col].select_previous()
                if chosen_col == 1:
                    chosen_ind = my_cols[chosen_col].chosen_ind
                    if len(self.papers)>0:
                        attributes = MainApp.get_paper_attributes(self.papers[chosen_ind])
                        my_cols[2].update(attributes, chosen_ind=0, start_index=0)
            elif c == ord('l'):
                if chosen_col<len(my_cols)-1:
                    my_cols[chosen_col].lost_focus()
                    chosen_col += 1
                    my_cols[chosen_col].get_focus()
            elif c == ord('h'):
                if chosen_col>0:
                    my_cols[chosen_col].lost_focus()
                    chosen_col -= 1
                    my_cols[chosen_col].get_focus()
            elif c == ord('G'):
                if chosen_col == 1:
                    my_cols[chosen_col].goto(-1)
                    if len(self.papers)>0:
                        attributes = MainApp.get_paper_attributes(self.papers[my_cols[1].chosen_ind])
                        my_cols[2].update(attributes, chosen_ind=0, start_index=0)
            elif c == ord('e'):
                if chosen_col == 0:
                    my_cols[chosen_col].expand()
            elif c == ord('c'):
                if chosen_col == 0:
                    my_cols[chosen_col].collapse()
            elif c == curses.KEY_ENTER or c == 10 or c == 13:
                if chosen_col == 0:
                    tags = my_cols[0].get_tags()
                    my_cols[0].update_current_item()
                    self.papers = self.database.get_list_papers(tags)
                    my_cols[1].update([paper['title'] for paper in
                        self.papers])
                    if len(self.papers)>0:
                        attributes = MainApp.get_paper_attributes(self.papers[my_cols[1].chosen_ind])
                        my_cols[2].update(attributes)
                elif chosen_col == 1:
                    relative_path = self.papers[my_cols[1].chosen_ind]['file']
                    current_path = os.path.dirname(os.path.abspath(__file__))
                    path_to_file = os.path.join(current_path, 'data', relative_path)
                    # print_me(stdscr, path_to_file)
                    if relative_path != '':
                        if os.path.exists(path_to_file):
                            program = 'zathura'
                            subprocess.Popen([program, path_to_file])
                        else:
                            status_bar.render('file not found')
                    else:
                        status_bar.render('no file')
            elif c== curses.KEY_RESIZE:
                self.tree_pos, self.col1_pos, self.col2_pos, _, is_enlarging = self.__estimate_layout()

                if is_enlarging:
                    my_cols[2].resize(self.col2_pos[0], self.col2_pos[1])
                    my_cols[2].move(self.col2_pos[2], self.col2_pos[3])

                    my_cols[1].resize(self.col1_pos[0], self.col1_pos[1])
                    my_cols[1].move(self.col1_pos[2], self.col1_pos[3])

                    my_cols[0].resize(self.tree_pos[0], self.tree_pos[1])
                else:
                    my_cols[0].resize(self.tree_pos[0], self.tree_pos[1])

                    my_cols[1].resize(self.col1_pos[0], self.col1_pos[1])
                    my_cols[1].move(self.col1_pos[2], self.col1_pos[3])

                    my_cols[2].resize(self.col2_pos[0], self.col2_pos[1])
                    my_cols[2].move(self.col2_pos[2], self.col2_pos[3])


                #
                # my_cols[0].render()
                # my_cols[1].render()
                # my_cols[2].render()
            elif c== 27:
                # Don't wait for another key
                # If it was Alt then curses has already sent the other key
                # otherwise -1 is sent (Escape)
                stdscr.nodelay(True)
                n = stdscr.getch()
                if n == -1:
                    # Escape was pressed
                    print_me(stdscr, 'escape')
                    status_bar.clear()
                # Return to delay
                stdscr.nodelay(False)
            elif c == ord('/'):
                # print_me(stdscr, 'backsplash')
                input_box.active()
            elif c == ord('V'):
                stdscr.refresh()
                curses.def_prog_mode()
                curses.endwin()
                relative_path = 'data/bib_collection.bib'
                current_path = os.path.dirname(os.path.abspath(__file__))
                path_to_file = os.path.join(current_path, relative_path)
                subprocess.check_call(['/usr/bin/vim', '+normal G$', path_to_file])
                curses.reset_prog_mode()
                stdscr.refresh()
            elif c== ord('r'):
                self.database.reload()
                collection_tree = self.database.get_collection()
                my_cols[0].update(collection_tree)
                first_collection = list(collection_tree.keys())[0]
                self.papers = self.database.get_list_papers([first_collection])
                list_items_1 = [paper['title'] for paper in self.papers]
                my_cols[1].update(list_items_1)
                if len(self.papers) > 0:
                    attributes = MainApp.get_paper_attributes(self.papers[my_cols[1].chosen_ind])
                else:
                    attributes = []
                my_cols[2].update(attributes)


    def get_paper_attributes(paper):
        return ['Title: ' + paper['title'].strip(),
                'Authors: ' + paper['author'].strip(),
                'Year: ' + str(paper['year']),
                'Venue: ' + str(paper['booktitle']),
                ]


def main(stdscr):
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    app = MainApp(stdscr)
    app.run()


if __name__ == "__main__":
    wrapper(main)


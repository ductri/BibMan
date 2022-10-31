import curses
from curses import wrapper
import random

from anytree import Node


from data.data_manager import DatabaseManager


def print_me(screen, msg):
    screen.addstr(0, 0, msg) # divide by zero


class ScrollableList(object):
    def __init__(self, pos, items, visible_off_focus=False, is_on_focus=True):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        self.begin_line = begin_line
        self.begin_col = begin_col
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
            if len(item) > self.ncols:
                item = item[:self.ncols-5] +' ...'

            if i == self.chosen_ind-self.start_index and self.is_on_focus:
                    self.win.addstr(item+'\n', curses.A_STANDOUT)
            elif i == self.secondary_chosen_ind-self.start_index and self.visible_off_focus:
                    self.win.addstr(item+'\n', curses.A_UNDERLINE)
            else:
                self.win.addstr(item+'\n')
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


class MainApp(object):
    def __init__(self):
        self.database = DatabaseManager()
        self.papers = self.database.get_list_papers(['default'])
        self.tree_pos = (10, 40, 1, 0) # (nlines, ncols, begin_line, begin_col)
        self.col1_pos = (10, 50, 1, 50) # (nlines, ncols, begin_line, begin_col)
        self.col2_pos = (10, 50, 1, 120) # (nlines, ncols, begin_line, begin_col)

    def run(self, stdscr):
        curses.curs_set(False)
        stdscr.clear()
        stdscr.refresh()

        collection_tree = self.database.get_collection()
        tree = TreeList(self.tree_pos, collection_tree)
        tree.render()

        list_items_1 = [paper['title'] for paper in self.papers]
        my_list1 = ScrollableList(self.col1_pos, list_items_1, is_on_focus=True)
        my_list1.render()

        list_items = MainApp.get_paper_attributes(self.papers[my_list1.chosen_ind])
        my_list2 = ScrollableList(self.col2_pos, list_items, is_on_focus=False, visible_off_focus=False)
        my_list2.render()

        my_cols = [tree, my_list1, my_list2]
        chosen_col = 1
        my_cols[chosen_col].get_focus()
        while True:
            c = stdscr.getch()
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
            elif c == ord('g'):
                my_cols[chosen_col].goto(50)
            elif c == ord('G'):
                my_cols[chosen_col].goto(-1)
            elif c == ord('e'):
                my_cols[chosen_col].expand()
            elif c == ord('c'):
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

    def get_paper_attributes(paper):
        return ['Authors: ' + ','.join(paper['author']),
                'Year: ' + str(paper['year']),
                'Venue: ' + str(paper['journal']),
                ]

def main(stdscr):
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    app = MainApp()
    app.run(stdscr)


if __name__ == "__main__":
    wrapper(main)


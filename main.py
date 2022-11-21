import curses
from curses import wrapper
import random
from subprocess import Popen, DEVNULL, STDOUT
import subprocess
import os
from curses.textpad import Textbox
import math
import re
import itertools
from datetime import datetime
import shutil

from anytree import Node, PreOrderIter
from anytree.resolver import Resolver, ChildResolverError
import pyperclip
import pdf2bib
from pdf2bib import pdf2bib_singlefile

from utils.data_manager import DatabaseManager
from utils.network_utils import download_file
from utils import others


def print_me(screen, msg, ncol=0):
    screen.addstr(0, ncol, msg) # divide by zero


class ScrollableList(object):
    def __init__(self, pos, items, visible_off_focus=False, is_on_focus=True, wrap=False):
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
        self.channels = dict()
        self.__crossed_inds = []
        self._offset_prefix = 0
        # self.__wrap = False
        """
        Got to implement such that we only care about chosen index, the visiable window should react accordingly.
        """

    def render(self):
        def decorate(item):
            lines = item.split('\n')
            new_lines = []
            for line in lines:
                line = line[self._offset_prefix:]
                if len(line) > self.ncols-1:
                    line = line[:self.ncols-6] +' ...'
                new_lines.append(line)
            new_item = '\n'.join(new_lines)
            return new_item

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

        current_line = 1
        for i in range(0, min(self.nlines-1, len(self.items) -self.start_index)):
            item = self.items[i+self.start_index]
            item = decorate(item)
            if i == self.chosen_ind-self.start_index and self.is_on_focus:
                self.win.addstr(current_line, 1, item, curses.A_STANDOUT)
            elif (i+self.start_index) in self.__crossed_inds:
                self.win.addstr(current_line, 1, item, curses.A_DIM)
            elif i == self.secondary_chosen_ind-self.start_index and self.visible_off_focus:
                self.win.addstr(current_line, 1, item, curses.A_UNDERLINE)
            else:
                self.win.addstr(current_line, 1, item)
            current_line += max(len(item.split('\n')),1)
        self.win.box()
        self.win.refresh()

    def select_next(self):
        if self.chosen_ind < len(self.items)-1:
            self.chosen_ind += 1
            self.render()

    def broadcast(self, event, channel):
        for listener in self.channels[channel]:
            listener.receive_event(event)

    def receive_event(self, event):
        pass

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

    def update(self, items, chosen_ind=0, start_index=0, secondary_chosen_ind=0, disable_inds=[]):
        self.items = items
        self.chosen_ind = min(chosen_ind, len(items)-1) # todo a very naive attempt to prevent exception
        self.start_index = min(start_index, len(items)-1) # todo a very naive attempt to prevent exception
        self.secondary_chosen_ind = min(secondary_chosen_ind, len(items)-1) # todo a very naive attempt to prevent exception
        self.__crossed_inds = disable_inds

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
        data = {'chosen_ind': self.chosen_ind, 'size': (self.nlines, self.ncols), \
                'items': self.items, 'start_index': self.start_index, \
                'offset': self.offset, 'channels': self.channels}
        return data

    def recover(self, data):
        self.chosen_ind = data['chosen_ind']
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


class TreeList(ScrollableList):
    def construct_tree(parent, mdict):
        for k, v in mdict.items():
            node = Node(k, parent=parent, expanded=False)
            TreeList.construct_tree(node, v)

    def __init__(self, database, pos, mdict=dict(), is_on_focus=False, default_tag_name='default'):
        """
        This class does too much business than it should!
        """

        nlines, ncols, begin_line, begin_col = pos
        self.database = database
        self.mdict = mdict
        self.tree = Node(default_tag_name, expanded=True)
        TreeList.construct_tree(self.tree, mdict)
        self.flatten_nodes = TreeList.render_tree(self.tree)
        ScrollableList.__init__(self, pos, [item.name for item in self.flatten_nodes], visible_off_focus=True, is_on_focus=is_on_focus)
        self.channels = dict()
        self._selected_node = None if len(self.flatten_nodes) == 0 else self.flatten_nodes[0] # The `selected node` could be different from the `chosen_ind` node, it is the item at the ENTER event.
        self.muted_nodes= []

    def lost_focus(self):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'tree'}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def expand(self):
        chosen_node = self.flatten_nodes[self.chosen_ind]
        chosen_node.expanded = True
        self.flatten_nodes = TreeList.render_tree(self.tree)
        ScrollableList.update(self, [' '*(node.depth-1)*2 + node.name for node in self.flatten_nodes], \
                chosen_ind=self.chosen_ind, start_index=self.start_index, \
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes))

    def collapse(self):
        chosen_node = self.flatten_nodes[self.chosen_ind]
        chosen_node.parent.expanded=False
        self.flatten_nodes = TreeList.render_tree(self.tree)
        new_secondary_chosen_ind = -1 if self._selected_node not in self.flatten_nodes else self.flatten_nodes.index(self._selected_node)
        ScrollableList.update(self, [' '*(node.depth-1)*2 + node.name for node in self.flatten_nodes], \
                chosen_ind=self.flatten_nodes.index(chosen_node.parent), start_index=self.start_index, \
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes))

    def __add_indent(flatten_nodes):
        return [' '*(node.depth-1)*2 + node.name for node in flatten_nodes]

    def render_tree(root):
        flatten_nodes = []
        for node in root.children:
            flatten_nodes.append(node)
            if node.expanded:
                flatten_nodes.extend(TreeList.render_tree(node))
        return flatten_nodes

    def __get_tags(self):
        if self._selected_node:
            return set(others.get_path(self._selected_node).split('/'))
        else:
            return set()

    def __get_neg_tags(self):
        return set(itertools.chain(*[others.get_path(n).split('/') for n in self.muted_nodes]))


    def get_current_item(self):
        """you are on thin ince"""
        return self.__get_tags()

    def init_data(self, mdict):
        self.tree = Node('default', expanded=True)
        TreeList.construct_tree(self.tree, mdict)
        self.flatten_nodes = TreeList.render_tree(self.tree)
        self._selected_node = self.flatten_nodes[0]
        ScrollableList.update(self, TreeList.__add_indent(self.flatten_nodes), \
                chosen_ind=self.chosen_ind, start_index=self.start_index,
                secondary_chosen_ind=self.flatten_nodes.index(self._selected_node))
        self.broadcast_new_collection()

    def broadcast_new_collection(self):
        event = {'name': 'NEW_COLLECTION', 'owner': 'tree', 'papers': self.database.get_list_papers(self.__get_tags())}
        self.broadcast(event, 0)

    def broadcast_request_update(self):
        event = {'name': 'UPDATE_COLLECTION', 'owner': 'tree', \
                'papers': self.database.get_list_papers(self.__get_tags(), self.__get_neg_tags())}
        self.broadcast(event, 0)

    def update(self, mdict):
        new_tree = Node('default', expanded=True)
        TreeList.construct_tree(new_tree, mdict)

        for node in PreOrderIter(self.tree):
            new_node = others.find_node(new_tree, others.get_path(node))
            if new_node:
                new_node.expanded = node.expanded
        self.tree = new_tree
        new_flatten_nodes = TreeList.render_tree(self.tree)

        self.flatten_nodes = new_flatten_nodes
        ScrollableList.update(self, TreeList.__add_indent(self.flatten_nodes), \
                chosen_ind=self.chosen_ind, start_index=self.start_index,
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes))
        self.broadcast_request_update()

    def toggle_mute(self):
        ind = others.get_node_index_from_list(self.flatten_nodes[self.chosen_ind], self.muted_nodes)
        if ind != -1:
            self.muted_nodes.remove(self.muted_nodes[ind])
        else:
            self.muted_nodes.append(self.flatten_nodes[self.chosen_ind])

        muted_inds = [others.get_node_index_from_list(n, self.flatten_nodes) for n in self.muted_nodes]
        ScrollableList.update(self, TreeList.__add_indent(self.flatten_nodes), \
                chosen_ind=self.chosen_ind, start_index=self.start_index,
                secondary_chosen_ind=others.get_node_index_from_list(self._selected_node, self.flatten_nodes),\
                disable_inds=muted_inds)
        self.broadcast_request_update()

    def receive_event(self, event):
        if event['owner'] == 'main_app':
            if event['name'] == 'DOWN':
                ScrollableList.select_next(self)
            elif event['name'] == 'UP':
                ScrollableList.select_previous(self)
            elif event['name'] == 'RIGHT':
                self.lost_focus()
            elif event['name'] == 'GOTO':
                line_number = event['line_number']
                ScrollableList.goto(self, line_number)
            elif event['name'] == 'ENTER':
                self._selected_node = self.flatten_nodes[self.chosen_ind]
                self.secondary_chosen_ind = self.chosen_ind
                self.broadcast_new_collection()
                self.render()
            elif event['name'] == 'EXPAND':
                self.expand()
            elif event['name'] == 'COLLAPSE':
                self.collapse()
            elif event['name'] == 'TOGGLE_MUTE':
                self.toggle_mute()
            elif event['name'] == 'SHIFT_RIGHT':
                self.shift_right()
            elif event['name'] == 'SHIFT_LEFT':
                self.shift_left()
        if event['owner'] == 'paper_col':
            if event['name'] == 'LOST_FOCUS':
                if event['direction'] == 'LEFT':
                    ScrollableList.get_focus(self)


class PaperCol(ScrollableList):
    def __init__(self, pos, papers, database, visible_off_focus=False, is_on_focus=False):
        self.__papers = papers # todo maybe we dont need this much info
        self.database = database
        items = [paper['title'] for paper in self.__papers]
        ScrollableList.__init__(self, pos, items, visible_off_focus=visible_off_focus, is_on_focus=is_on_focus)

    def __set_papers(self, papers):
        self.__papers = sorted(papers, \
                key=lambda p: datetime.strptime(p['created_time'], DatabaseManager.DATETIME_FORMAT),\
                reverse=True
                )

    def get_papers(self):
        return self.__papers

    def receive_event(self, event):
        if event['owner'] == 'main_app':
            if event['name'] == 'UPDATE_COLLECTION':
                self.update(event['papers'])
                self.start_index(0)
            elif event['name'] == 'NEW_COLLECTION':
                new_list_papers = event['papers']
                self.update(new_list_papers)
                self.goto(0)
                self.broadcast_new_paper()
            elif event['name'] == 'DOWN':
                self.select_next()
            elif event['name'] == 'UP':
                self.select_previous()
            elif event['name'] == 'RIGHT':
                self.lost_focus('RIGHT')
            elif event['name'] == 'GOTO':
                line_number = event['line_number']
                self.goto(line_number)
            elif event['name'] == 'LEFT':
                self.lost_focus('LEFT')
            elif event['name'] == 'ENTER':
                relative_path = self.__papers[self.chosen_ind]['file']
                event = {'name': 'ASK_OPEN_FILE', 'owner': 'paper_col', 'relative_path': relative_path}
                self.broadcast(event, 1)
            elif event['name'] == 'COPY_BIB':
                pyperclip.copy(self.get_bib())
                event = {'name': 'COPY_TO_CLIPBOARD', 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'new_collection': # todo why is it still here?
                tags = event['tags']
                new_list_papers = self.database.get_list_papers(tags)
                self.update(new_list_papers)
                # self.goto(0)
            elif event['name'] == 'REQUEST_OPEN_BIB_FILE':
                event = {'name': 'ASK_OPEN_BIB', 'paper_id': self.__papers[self.chosen_ind]['ID'], 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'REMOVE_PAPER':
                event = {'name': 'RESP_REMOVE_PAPER', 'paper_id': self.__papers[self.chosen_ind]['ID'], 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'EVINCE':
                event = {'name': 'RESP_EVINCE', 'relative_path': self.__papers[self.chosen_ind]['file'], 'owner': 'paper_col'}
                self.broadcast(event, 1)

        elif event['owner'] == 'att_col':
            if event['name'] == 'LOST_FOCUS':
                ScrollableList.get_focus(self)
        elif event['owner'] == 'tree':
            if event['name'] == 'LOST_FOCUS':
                ScrollableList.get_focus(self)
            elif event['name'] == 'NEW_COLLECTION':
                new_list_papers = event['papers']
                self.update(new_list_papers)
                self.goto(0)
                self.broadcast_new_paper()
            elif event['name'] == 'UPDATE_COLLECTION':
                new_list_papers = event['papers']
                self.update(new_list_papers)
                self.broadcast_request_update()

    def get_bib(self):
        return others.export_bib_format(self.__papers[self.chosen_ind])

    def lost_focus(self, direction):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'paper_col', 'direction': direction}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def broadcast_new_paper(self):
        if len(self.__papers)>0:
            event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper': self.__papers[self.chosen_ind]}
        else:
            event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper': None}
        self.broadcast(event, 0)

    def broadcast_request_update(self):
        event = {'name': 'UPDATE_PAPER', 'owner': 'paper_col', 'paper': self.__papers[self.chosen_ind]}
        self.broadcast(event, 0)

    def select_next(self):
        ScrollableList.select_next(self)
        self.broadcast_new_paper()

    def select_previous(self):
        ScrollableList.select_previous(self)
        self.broadcast_new_paper()

    def goto(self, line_number):
        ScrollableList.goto(self, line_number)
        self.broadcast_new_paper()

    def update(self, papers):
        self.__set_papers(papers)
        items = [paper['title'] for paper in self.__papers]
        ScrollableList.update(self, items, chosen_ind=self.chosen_ind, start_index=self.start_index)

    def get_current_paper(self):
        return self.__papers[self.chosen_ind]

    def dump(self):
        data = ScrollableList.dump(self)
        data['papers'] = self.__papers
        data['database'] = self.database
        return data

    def recover(self, data):
        self.__set_papers(data['papers'])
        self.database = data['database']
        ScrollableList.recover(self, data)


class AttCol(ScrollableList):
    ATTRIBUTES = [('title', 'Title: '), ('author','Authors: '), ('year', 'Year: '), ('booktitle', 'Venue: '), ('created_time',  'Created: ')]
    def __init__(self, pos, paper, database, visible_off_focus=True, is_on_focus=False):
        self.database = database
        if paper:
            self.atts = AttCol.get_paper_attributes(paper)
        else:
            self.atts = []
        items = self.add_decoration(self.atts)
        ScrollableList.__init__(self, pos, items, visible_off_focus=visible_off_focus, is_on_focus=is_on_focus, wrap=True)

    def add_decoration(self, attr_values):
        def title2lines(title):
            max_lines = 4
            head_len = max(self.ncols-10, 0)
            head = title[:head_len]
            tail = title[head_len:]
            step = self.ncols - 3
            lines = ['  ' + tail[i:i+step] for i in range(0, len(tail), step)]
            if len(lines) > max_lines:
                lines = lines[:max_lines-1] + ['   ...']
            else:
                lines = lines + ['']*(max_lines - len(lines))
            lines = [head] + lines
            return lines

        def author2lines(author_str):
            max_lines = 4
            lines = [' - ' + author.strip() for author in author_str.split('and')]
            if len(lines)>max_lines:
                lines = lines[:max_lines-1] + [' ...']
            else:
                lines = lines + [''] * (max_lines-len(lines))
            lines = [''] + lines
            return lines

        results = []
        for ((attr_key, attr_name), attr_value) in zip(AttCol.ATTRIBUTES, attr_values):
            if attr_key == 'created_time':
                results.append(attr_name + '\n    ' + attr_value)
            elif attr_key == 'title':
                lines = title2lines(attr_value)
                results.append(attr_name + '\n'.join(lines))
            elif attr_key == 'author':
                lines = author2lines(attr_value)
                results.append(attr_name + '\n'.join(lines))
            elif attr_key == 'year':
                lines = [attr_value, '']
                results.append(attr_name + '\n'.join(lines))
            elif attr_key == 'booktitle':
                head_len = max(self.ncols-10, 0)
                head = attr_value[:head_len]
                tail = attr_value[head_len:]
                step = self.ncols - 3
                lines = ['  ' + tail[i:i+step] for i in range(0, len(tail), step)]
                lines = [head] + lines +['']
                results.append(attr_name + '\n'.join(lines))
            else:
                results.append(attr_name + attr_value)
        return results

    def get_paper_attributes(paper):
        if paper:
            return [paper[item[0]] for item in AttCol.ATTRIBUTES]
        else:
            return []

    def receive_event(self, event):
        if event['owner'] == 'paper_col':
            if event['name'] == 'NEW_PAPER':
                paper = event['paper']
                self.update(paper)
                self.goto(0)
            elif event['name'] == 'UPDATE_PAPER':
                paper = event['paper']
                self.update(paper)
            elif event['name'] == 'LOST_FOCUS':
                if event['direction'] == 'RIGHT':
                    ScrollableList.get_focus(self)
        elif event['owner'] == 'main_app':
            if event['name'] == 'DOWN':
                ScrollableList.select_next(self)
            elif event['name'] == 'UP':
                ScrollableList.select_previous(self)
            elif event['name'] == 'GOTO':
                line_number = event['line_number']
                ScrollableList.goto(self, line_number)
            elif event['name'] == 'LEFT':
                self.give_focus_to_left()
            elif event['name'] == 'ENTER':
                pyperclip.copy(self.atts[self.chosen_ind])
                event = {'name': 'COPY_TO_CLIPBOARD', 'owner': 'att_col'}
                self.broadcast(event, 1)

    def give_focus_to_left(self):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'att_col'}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def update(self, paper):
        self.atts = AttCol.get_paper_attributes(paper)
        items = self.add_decoration(self.atts)
        ScrollableList.update(self, items, chosen_ind=self.chosen_ind, start_index=self.start_index)


class Menu(ScrollableList):
    def __init__(self, pos, items, visible_off_focus=False, is_on_focus=True):
        ScrollableList.__init__(self, pos, items)

    def disappear(self):
        self.win.clear()
        self.win.refresh()


class Status(object):
    def __init__(self, pos):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)

    def update(self, msg):
        self.win.erase()
        if len(msg) > self.ncols:
            msg = msg[:self.ncols-6] +' ...'
        self.win.addstr(0, 1, msg)
        self.win.refresh()

    def clear(self):
        self.win.erase()
        self.win.refresh()

    def move(self, y, x):
        self.clear()
        self.win.mvwin(y, x)

    def resize(self, nlines, ncols):
        self.clear()
        self.win.resize(nlines, ncols)
        self.nlines = nlines
        self.ncols = ncols


class MyInput(object):
    def __init__(self, pos):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)
        self.box = Textbox(self.win)
        self.text = ''

    def active(self):
        self.win.erase()
        self.text = ''
        curses.curs_set(True)
        while True:
            c = self.win.getch()
            if c == curses.KEY_ENTER or c == 10 or c == 13:
                break
            elif c == curses.KEY_BACKSPACE or c == curses.KEY_DC or c == 127:
                if len(self.text) > 0:
                    self.text = self.text[:-1]
                    self.win.erase()
            else:
                self.text += chr(c)
            self.win.addstr(0, 0, self.text[-self.ncols+10:])
        curses.curs_set(False)
        self.win.erase()

    def get(self):
        return self.text

    def clear(self):
        self.win.erase()
        self.win.refresh()

    def move(self, y, x):
        self.clear()
        self.win.mvwin(y, x)

    def resize(self, nlines, ncols):
        self.clear()
        self.win.resize(nlines, ncols)
        self.nlines = nlines
        self.ncols = ncols


class MyInputDeprecated(object):
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
    def get_layout(max_nlines, max_ncols):
        nlines = max_nlines
        ncols = max_ncols
        space = 2
        height = nlines-3
        is_enlarging = False
        layout_ratio = (0.1, 0.7, 0.2)
        list_ncols = [math.floor(layout_ratio[0]*ncols), math.floor(layout_ratio[1]*ncols)]
        tmp = sum(list_ncols)
        list_ncols[0] = max(list_ncols[0], 23)
        list_ncols[1] = tmp - list_ncols[0]
        list_ncols.append(ncols - list_ncols[0] - list_ncols[1]-2*space-2)

        tree_pos = (height, list_ncols[0], 1, 1) # (nlines, ncols, begin_line, begin_col)
        col1_pos = (height, list_ncols[1], 1, 1+list_ncols[0]+space) # (nlines, ncols, begin_line, begin_col)
        col2_pos = (height, list_ncols[2], 1, 1+list_ncols[0] + space+list_ncols[1]+space) # (nlines, ncols, begin_line, begin_col)

        positions_dict = dict()
        positions_dict['tree'] = tree_pos
        positions_dict['paper_col'] = col1_pos
        positions_dict['att_col'] = col2_pos
        positions_dict['status_bar'] = (1, ncols-2, nlines-2, 1)
        positions_dict['input_box'] = (1, ncols-3, nlines-2, 3)
        positions_dict['menu'] = (0, 0, 10, 10)
        return positions_dict

    def get_size(self):
        return self.stdscr.getmaxyx()

    def __init__(self, stdscr):
        self.channels = dict()
        self.database = DatabaseManager()
        pdf2bib.config.set('verbose',False)

        self.stdscr = stdscr
        curses.curs_set(False)
        stdscr.clear()
        stdscr.refresh()

        self.global_state = {'current_component':  'paper_col', 'alternative_gui_visible': False}
        self.max_nlines, self.max_ncols = self.get_size()
        self.positions_dict = MainApp.get_layout(self.max_nlines, self.max_ncols)
        self.component_dict = dict()
        self.component_dict['tree'] = TreeList(self.database, self.positions_dict['tree'])
        self.component_dict['paper_col'] = PaperCol(self.positions_dict['paper_col'], [], self.database, visible_off_focus=False, is_on_focus=True)
        self.component_dict['paper_col'].listen_to(self.component_dict['tree'], channel=0)
        self.component_dict['att_col'] = AttCol(self.positions_dict['att_col'], None, self.database, is_on_focus=False, visible_off_focus=False)
        self.component_dict['att_col'].listen_to(self.component_dict['paper_col'], channel=0)
        self.component_dict['paper_col'].listen_to(self.component_dict['att_col'], channel=0)
        self.component_dict['tree'].listen_to(self.component_dict['paper_col'], channel=0)

        self.component_dict['status_bar'] = Status(self.positions_dict['status_bar'])
        self.component_dict['input_box'] = MyInput(self.positions_dict['input_box'])
        self.component_dict['menu'] = Menu(self.positions_dict['menu'], [])

        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.init_data()
        self.listen_to(self.component_dict['tree'], 1)
        self.listen_to(self.component_dict['paper_col'], 1)
        self.listen_to(self.component_dict['att_col'], 1)
        self.searched_papers = []

    def init_data(self):
        """
        Different from `update_data`: It decides the initial GUI state: chosen_ind, secondary_chosen_ind, fold/expand, ...
        """
        collection_tree = self.database.get_collection()
        self.component_dict['tree'].init_data(collection_tree)

    def update_data(self):
        """
        Different from `init_data`: It tries to retain as much as possible current state: chosen_ind, secondary_chosen_ind, current fold/expand, ...
        """
        collection_tree = self.database.get_collection()
        self.component_dict['tree'].update(collection_tree)

    def reload(self):
        self.database.reload()
        self.update_data()
        self.notify_user('Updated')

    def update_interface_only(self):
        max_nlines, max_ncols = self.get_size()
        wide_enlarger = False
        if max_ncols>self.max_ncols:
            wide_enlarger = True
        self.max_nlines = max_nlines
        self.max_ncols = max_ncols

        self.positions_dict = MainApp.get_layout(max_nlines, max_ncols)
        if wide_enlarger:
            self.component_dict['status_bar'].resize(self.positions_dict['status_bar'][0], self.positions_dict['status_bar'][1])
            self.component_dict['status_bar'].move(self.positions_dict['status_bar'][2], self.positions_dict['status_bar'][3])
            self.component_dict['input_box'].resize(self.positions_dict['input_box'][0], self.positions_dict['input_box'][1])
            self.component_dict['input_box'].move(self.positions_dict['input_box'][2], self.positions_dict['input_box'][3])

            sizes = (self.positions_dict['att_col'][0], self.positions_dict['att_col'][1])
            self.component_dict['att_col'].resize(sizes[0], sizes[1])
            pos = (self.positions_dict['att_col'][2], self.positions_dict['att_col'][3])
            self.component_dict['att_col'].move(pos[0], pos[1])

            sizes = (self.positions_dict['paper_col'][0], self.positions_dict['paper_col'][1])
            self.component_dict['paper_col'].resize(sizes[0], sizes[1])
            pos = (self.positions_dict['paper_col'][2], self.positions_dict['paper_col'][3])
            self.component_dict['paper_col'].move(pos[0], pos[1])

            sizes = (self.positions_dict['tree'][0], self.positions_dict['tree'][1])
            self.component_dict['tree'].resize(sizes[0], sizes[1])
        else:
            sizes = (self.positions_dict['tree'][0], self.positions_dict['tree'][1])
            self.component_dict['tree'].resize(sizes[0], sizes[1])

            sizes = (self.positions_dict['paper_col'][0], self.positions_dict['paper_col'][1])
            self.component_dict['paper_col'].resize(sizes[0], sizes[1])
            pos = (self.positions_dict['paper_col'][2], self.positions_dict['paper_col'][3])
            self.component_dict['paper_col'].move(pos[0], pos[1])

            sizes = (self.positions_dict['att_col'][0], self.positions_dict['att_col'][1])
            self.component_dict['att_col'].resize(sizes[0], sizes[1])
            pos = (self.positions_dict['att_col'][2], self.positions_dict['att_col'][3])
            self.component_dict['att_col'].move(pos[0], pos[1])

            self.component_dict['status_bar'].resize(self.positions_dict['status_bar'][0], self.positions_dict['status_bar'][1])
            self.component_dict['status_bar'].move(self.positions_dict['status_bar'][2], self.positions_dict['status_bar'][3])
            self.component_dict['input_box'].resize(self.positions_dict['input_box'][0], self.positions_dict['input_box'][1])
            self.component_dict['input_box'].move(self.positions_dict['input_box'][2], self.positions_dict['input_box'][3])

    def run(self):
        while True:
            c = self.component_dict['status_bar'].win.getch()
            if c == ord('q'):
                break
            elif c == ord('j'):
                event = {'name': 'DOWN', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                self.notify_user('') # this is quite a not good hack
            elif c == ord('k'):
                event = {'name': 'UP', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                self.notify_user('') # this is quite a not good hack
            elif c == ord('l'):
                event = {'name': 'RIGHT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('h'):
                event = {'name': 'LEFT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('G'):
                event = {'name': 'GOTO', 'owner': 'main_app', 'line_number': -1}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('e'):
                event = {'name': 'EXPAND', 'owner':  'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('c'):
                event = {'name': 'COLLAPSE', 'owner':  'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == curses.KEY_ENTER or c == 10 or c == 13:
                event = {'name': 'ENTER', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c== curses.KEY_RESIZE:
                self.update_interface_only()
            elif c == ord('V'):
                event = {'name': 'REQUEST_OPEN_BIB_FILE', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c== ord('r'):
                self.reload()
            elif c == ord(':'):
                command_info = self.wait_for_command()
                self.perform_command(command_info)
            elif c == ord('S'):
                self.global_state['alternative_gui_visible'] = not self.global_state['alternative_gui_visible']
                if self.global_state['alternative_gui_visible']:
                    self.search_on()
                else:
                    self.search_off()
            elif c == ord('m'):
                event = {'name': 'TOGGLE_MUTE', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('/'):
                command_info = self.wait_for_command(search=True)
                self.perform_command(command_info)
            elif c == ord(']'):
                event = {'name': 'SHIFT_RIGHT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('['):
                event = {'name': 'SHIFT_LEFT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)

    def search_on(self):
        if not self.global_state['alternative_gui_visible']:
            self.global_state['paper_col_data'] = self.component_dict['paper_col'].dump()
        event = {'name': 'NEW_COLLECTION',  'papers': self.searched_papers, 'owner': 'main_app'}
        self.component_dict['paper_col'].receive_event(event)
        self.notify_user('Showing search GUI')

    def search_off(self):
        self.component_dict['paper_col'].recover(self.global_state['paper_col_data'])
        self.notify_user('Back to main GUI')

    def wait_for_command(self, search=False):
        command_info = dict()

        if search:
            self.notify_user('/')
        else:
            self.notify_user(':')
        self.component_dict['input_box'].active()
        command = self.component_dict['input_box'].get()

        if search:
            if command[:5] == 'title':
                command_info = {'name': 'SEARCH_TITLE', 'key': command[5:].strip()}
            else:
                command_info = {'name': 'SEARCH_TITLE', 'key': command.strip()}
        else:
            if command[:8] == 'download':
                command_info = {'name': 'DOWNLOAD', 'paper_id': self.component_dict['paper_col'].get_current_paper()['ID'], 'url': command[9:].strip()}
            elif command[:10] == 'update_pdf':
                command_info = {'name': 'UPDATE_PDF', 'paper_id': self.component_dict['paper_col'].get_current_paper()['ID'], 'url': command[11:].strip()}
            elif command[:8] == 'copy_bib':
                event = {'name': 'COPY_BIB', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command[:9] == 'add_paper':
                command_info = {'name': 'ADD_PAPER', 'owner': 'main_app', 'title': command[9:].strip()}
            elif command[:9] == 'paper_url':
                command_info = {'name': 'ADD_PAPER_URL', 'owner': 'main_app', 'url': command[9:].strip()}
            elif command[:12] == 'remove_paper':
                command_info = {'name': 'REMOVE_PAPER', 'owner': 'main_app'}
            elif command[:6] == 'evince':
                command_info = {'name': 'EVINCE', 'owner': 'main_app'}
            elif command[:7] == 's_title':
                command_info = {'name': 'SEARCH_TITLE', 'key': command[7:].strip()}
            elif command[:14] == 'add_local_file':
                command_info = {'name': 'ADD_LOCAL_FILE', 'paper_id': self.component_dict['paper_col'].get_current_paper()['ID'], 'path': command[14:].strip()}
            elif command[:7] == 'add_tag':
                command_info = {'name': 'ADD_TAG', 'tag': command[7:].strip()}
            else:
                command_info = {'name': 'UNDEFINED', 'message': command.strip()}
        return command_info

    def perform_command(self, command_info):
        if command_info['name'] == 'DOWNLOAD':
            self.notify_user('Performing command DOWNLOAD ...')

            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(self.current_path, 'data', 'pdfs', filename)
            if download_file(command_info['url'], path_to_file):
                self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
                self.notify_user('Downloading ... Done')
            else:
                self.notify_user('Downloading ... Failed.')
        elif command_info['name'] == 'ADD_LOCAL_FILE':
            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(self.current_path, 'data', 'pdfs', filename)
            src = command_info['path']
            shutil.copyfile(src, path_to_file)
            self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
            self.notify_user('Added file.')
        elif command_info['name'] == 'UPDATE_PDF':
            self.notify_user('Performing command UPDATE_PDF ... Downloading pdf..')

            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(self.current_path, 'data', 'pdfs', filename)
            if download_file(command_info['url'], path_to_file):
                self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
                self.notify_user('Downloading ... Done. Updated file')
            else:
                self.notify_user('Downloading ... Failed.')
        elif command_info['name'] == 'UNDEFINED':
            text = 'You entered an undefined command: "%s"' % command_info['message'] # hard code 5
            self.notify_user(text)
        elif command_info['name'] == 'ADD_PAPER':
            title = command_info['title']
            self.database.add_paper({'title': title, 'tags': self.component_dict['tree'].get_current_item()})
            self.update_data()

            self.notify_user('Added a paper')
        elif command_info['name'] == 'ADD_PAPER_URL':
            self.notify_user('Downloading ...')
            url = command_info['url']
            filename = str(random.randint(0, 100000000000))
            path_to_file = os.path.join(self.current_path, 'data', 'pdfs', '%s.pdf'%filename)
            download_result = download_file(url, path_to_file)
            if download_result:
                self.notify_user('Retrieving bib info ...')
                result = pdf2bib_singlefile(path_to_file)
                info = result['metadata']
                paper_dict = others.format_bib(info, path_to_file)
                paper_dict['file'] = path_to_file
                paper_dict['tags'] = self.component_dict['tree'].get_current_item()
                if 'journal' in info:
                    paper_dict['journal'] = info['journal']
                self.database.add_paper(paper_dict)
                self.update_data()
                self.notify_user('Added a paper')
            else:
                self.notify_user('Downloading ... Failed.')
        elif command_info['name'] == 'REMOVE_PAPER':
            event = {'name': 'REMOVE_PAPER', 'owner': 'main_app'}
            self.component_dict[self.global_state['current_component']].receive_event(event)
        elif command_info['name'] == 'EVINCE':
            event = {'name': 'EVINCE', 'owner': 'main_app'}
            self.component_dict[self.global_state['current_component']].receive_event(event)
        elif command_info['name'] == 'SEARCH_TITLE':
            self.searched_papers = others.search_title(self.component_dict['paper_col'].get_papers(), command_info['key'])
            self.search_on()
            self.global_state['alternative_gui_visible'] = True
        elif command_info['name'] == 'ADD_TAG':
            paper = self.component_dict['paper_col'].get_current_paper()
            tag = command_info['tag']
            paper_id = paper['ID']
            self.database.update_paper(paper_id, 'tags', paper['tags'] | set([tag]))
            self.notify_user('Added tag "%s" to paper id "%s"'% (tag, paper_id))


    def open_paper_external(self, relative_path, program='evince'):
        path_to_file = os.path.join(self.current_path, 'data', relative_path)
        if os.path.isfile(path_to_file):
            Popen([program, path_to_file], stdout=DEVNULL, stderr=STDOUT)
            self.notify_user('opened paper successfully')
        else:
            pass
            self.notify_user('file not found')

    def notify_user(self, message):
        self.component_dict['status_bar'].update(message)

    def open_bib_file(self, key='53314681848'):
        self.stdscr.refresh()
        curses.def_prog_mode()
        curses.endwin()
        relative_path = 'data/bib_collection.bib'
        current_path = os.path.dirname(os.path.abspath(__file__))
        path_to_file = os.path.join(current_path, relative_path)
        subprocess.run(['/usr/bin/vim', '-c silent! /%s'%key, path_to_file])
        curses.reset_prog_mode()
        self.reload()
        self.stdscr.refresh()

    def add_listener(self, listener, channel):
        if channel in self.channels:
            self.channels[channel].append(listener)
        else:
            self.channels[channel] = [listener]

    def listen_to(self, host, channel):
        host.add_listener(self, channel)

    def receive_event(self, event):
        if event['owner'] == 'tree':
            if event['name'] == 'LOST_FOCUS':
                self.global_state['current_component'] = 'paper_col'
        elif event['owner'] == 'paper_col':
            if event['name'] == 'OPEN_FILE_EXTERNAL':
                code = event['code']
                msg = event['message']
                self.component_dict['status_bar'].update(msg)
            elif event['name'] == 'LOST_FOCUS':
                if event['direction'] == 'LEFT':
                    self.global_state['current_component'] = 'tree'
                elif event['direction'] == 'RIGHT':
                    self.global_state['current_component'] = 'att_col'
            elif event['name'] == 'COPY_TO_CLIPBOARD':
                self.notify_user('Text is sent to clipboard')
            elif event['name'] == 'ASK_OPEN_FILE':
                self.open_paper_external(event['relative_path'])
            elif event['name'] == 'ASK_OPEN_BIB':
                self.open_bib_file(event['paper_id'])
            elif event['name'] == 'RESP_REMOVE_PAPER':
                self.database.remove_paper(event['paper_id'])
                self.notify_user('Paper ID: %s has been removed' % event['paper_id'])
                self.reload()
            elif event['name'] == 'RESP_EVINCE':
                self.open_paper_external(event['relative_path'], program='evince')
        elif event['owner'] == 'att_col':
            if event['name'] == 'LOST_FOCUS':
                self.global_state['current_component'] = 'paper_col'
            elif event['name'] == 'COPY_TO_CLIPBOARD':
                self.notify_user('Text is sent to clipboard')


def main(stdscr):
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    app = MainApp(stdscr)
    app.run()


if __name__ == "__main__":
    wrapper(main)


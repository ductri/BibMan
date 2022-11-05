import curses
from curses import wrapper
import random
import subprocess
import os
from curses.textpad import Textbox
import math
import re

from anytree import Node, PreOrderIter
from anytree.resolver import Resolver, ChildResolverError
import pyperclip


from utils.data_manager import DatabaseManager
from utils.network_utils import download_file
from utils import others


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
        self.channels = dict()
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

    def update(self, items, chosen_ind=0, start_index=0):
        self.items = items
        self.chosen_ind = min(chosen_ind, len(items)) # todo a very naive attempt to prevent exception
        self.start_index = min(start_index, len(items)) # todo a very naive attempt to prevent exception
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


class TreeList(ScrollableList):
    def construct_tree(parent, mdict):
        for k, v in mdict.items():
            node = Node(k, parent=parent, expanded=False)
            TreeList.construct_tree(node, v)

    def __init__(self, pos, mdict=dict(), is_on_focus=False, default_tag_name='default'):
        """
        This class does too much business than it should!
        """

        nlines, ncols, begin_line, begin_col = pos
        self.mdict = mdict
        self.tree = Node(default_tag_name, expanded=True)
        TreeList.construct_tree(self.tree, mdict)
        self.flatten_nodes = TreeList.render_tree(self.tree)
        ScrollableList.__init__(self, pos, [item.name for item in self.flatten_nodes], visible_off_focus=False, is_on_focus=is_on_focus)
        self.channels = dict()

    def lost_focus(self):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'tree'}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def expand(self):
        chosen_node = self.flatten_nodes[self.chosen_ind]
        chosen_node.expanded = True
        self.flatten_nodes = TreeList.render_tree(self.tree)
        ScrollableList.update(self, [' '*(node.depth-1)*2 + node.name for node in self.flatten_nodes], chosen_ind=self.chosen_ind, start_index=self.start_index)

    def collapse(self):
        chosen_node = self.flatten_nodes[self.chosen_ind]
        chosen_node.parent.expanded=False
        self.flatten_nodes = TreeList.render_tree(self.tree)
        ScrollableList.update(self, [' '*(node.depth-1)*2 + node.name for node in self.flatten_nodes], chosen_ind=self.flatten_nodes.index(chosen_node.parent), start_index=self.start_index)

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
        return set(others.get_path(self.flatten_nodes[self.chosen_ind]).split('/'))

    def get_current_item(self):
        return self.__get_tags()

    def update_current_item(self):
        event = {'name':  'new_collection',  'tags': self.__get_tags(), 'owner':  'tree'}
        ScrollableList.broadcast(self, event, 0)

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
                chosen_ind=self.chosen_ind, start_index=self.start_index)


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
                self.update_current_item()
            elif event['name'] == 'EXPAND':
                self.expand()
            elif event['name'] == 'COLLAPSE':
                self.collapse()
        if event['owner'] == 'paper_col':
            if event['name'] == 'LOST_FOCUS':
                if event['direction'] == 'LEFT':
                    ScrollableList.get_focus(self)



class PaperCol(ScrollableList):
    def __init__(self, pos, papers, database, visible_off_focus=False, is_on_focus=False):
        self.papers = papers # todo maybe we dont need this much info
        self.database = database
        items = [paper['title'] for paper in self.papers]
        ScrollableList.__init__(self, pos, items, visible_off_focus=visible_off_focus, is_on_focus=is_on_focus)

    def receive_event(self, event):
        if event['owner'] == 'main_app':
            if event['name'] == 'UPDATE_COLLECTION':
                self.update(event['papers'])
                self.start_index(0)
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
                path_to_file = self.database.get_paper_path(self.papers[self.chosen_ind]['ID'])
                status = self.open_paper_external(path_to_file)
                self.notify(status)
            elif event['name'] == 'COPY_BIB':
                pyperclip.copy(self.get_bib())
                event = {'name': 'COPY_TO_CLIPBOARD', 'owner': 'paper_col'}
                self.broadcast(event, 1)
        elif event['owner'] == 'att_col':
            if event['name'] == 'LOST_FOCUS':
                ScrollableList.get_focus(self)
        elif event['owner'] == 'tree':
            if event['name'] == 'LOST_FOCUS':
                ScrollableList.get_focus(self)
            elif event['name'] == 'new_collection':
                tags = event['tags']
                new_list_papers = self.database.get_list_papers(tags)
                self.update(new_list_papers)
                self.goto(0)

    def get_bib(self):
        return others.export_bib_format(self.papers[self.chosen_ind])

    def notify(self, status):
        # todo well, maybe this function is not that useful
        event = {'name': 'OPEN_FILE_EXTERNAL', 'owner': 'paper_col', 'code': status['code'], 'message': status['message']}
        self.broadcast(event, 1)

    def open_paper_external(self, path_to_file):
        if os.path.isfile(path_to_file):
            program = 'zathura'
            subprocess.Popen([program, path_to_file])
            status = {'code': 0, 'message': 'opened paper successfully'}
        else:
            status = {'code': 1, 'message': 'file not found'}
        return status

    def lost_focus(self, direction):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'paper_col', 'direction': direction}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def select_next(self):
        ScrollableList.select_next(self)
        event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper_id': self.papers[self.chosen_ind]['ID']}
        self.broadcast(event, 0)

    def select_previous(self):
        ScrollableList.select_previous(self)
        event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper_id': self.papers[self.chosen_ind]['ID']}
        self.broadcast(event, 0)

    def goto(self, line_number):
        ScrollableList.goto(self, line_number)
        event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper_id': self.papers[self.chosen_ind]['ID']}
        self.broadcast(event, 0)

    def update(self, papers):
        self.papers = papers
        items = [paper['title'] for paper in self.papers]
        ScrollableList.update(self, items, chosen_ind=self.chosen_ind, start_index=self.start_index)

    def get_current_paper(self):
        return self.papers[self.chosen_ind]

    def dump(self):
        data = ScrollableList.dump(self)
        data['papers'] = self.papers
        data['database'] = self.database
        return data

    def recover(self, data):
        self.papers = data['papers']
        self.database = data['database']
        ScrollableList.recover(self, data)


class AttCol(ScrollableList):
    def __init__(self, pos, items, database, visible_off_focus=True, is_on_focus=False):
        ScrollableList.__init__(self, pos, items, visible_off_focus=visible_off_focus, is_on_focus=is_on_focus)
        self.database = database

    def receive_event(self, event):
        if event['owner'] == 'paper_col':
            if event['name'] == 'NEW_PAPER':
                paper_id = event['paper_id']
                att = self.database.get_paper_attributes(paper_id)
                self.update(att)
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
                pyperclip.copy(self.items[self.chosen_ind])
                event = {'name': 'COPY_TO_CLIPBOARD', 'owner': 'att_col'}
                self.broadcast(event, 1)

    def give_focus_to_left(self):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'att_col'}
        self.broadcast(event, 0)
        self.broadcast(event, 1)


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
    """
    Super BUGGY here, need a layer manager or something like that.
    """
    def get_layout(max_nlines, max_ncols):
        nlines = max_nlines
        ncols = max_ncols
        padding = 3
        height = min(30, nlines)
        is_enlarging = False
        layout_ratio = (0.1, 0.6, 0.3)
        list_ncols = [math.floor(layout_ratio[0]*ncols), math.floor(layout_ratio[1]*ncols)]
        list_ncols.append(ncols - list_ncols[0] - list_ncols[1]-2*padding-2)
        tree_pos = (height, list_ncols[0], 1, 1) # (nlines, ncols, begin_line, begin_col)
        col1_pos = (height, list_ncols[1], 1, 1+list_ncols[0]+padding) # (nlines, ncols, begin_line, begin_col)
        col2_pos = (height, list_ncols[2], 1, 1+list_ncols[0] + padding+list_ncols[1]+padding) # (nlines, ncols, begin_line, begin_col)
        status_pos = (1, ncols, nlines-1, 1)

        positions_dict = dict()
        positions_dict['tree'] = tree_pos
        positions_dict['paper_col'] = col1_pos
        positions_dict['att_col'] = col2_pos
        positions_dict['status_bar'] = status_pos
        positions_dict['input_box'] = (status_pos[0], status_pos[1], status_pos[2], 3)
        positions_dict['menu'] = (0, 0, 10, 10)
        return positions_dict

    def get_size(self):
        return self.stdscr.getmaxyx()

    def __init__(self, stdscr):
        self.channels = dict()
        self.database = DatabaseManager()

        self.stdscr = stdscr
        curses.curs_set(False)
        stdscr.clear()
        stdscr.refresh()

        self.global_state = {'current_component':  'paper_col', 'alternative_gui_visible': False}
        self.max_nlines, self.max_ncols = self.get_size()
        self.positions_dict = MainApp.get_layout(self.max_nlines, self.max_ncols)
        self.component_dict = dict()
        self.component_dict['tree'] = TreeList(self.positions_dict['tree'])
        self.component_dict['paper_col'] = PaperCol(self.positions_dict['paper_col'], [], self.database, visible_off_focus=False, is_on_focus=True)
        self.component_dict['paper_col'].listen_to(self.component_dict['tree'], channel=0)
        self.component_dict['att_col'] = AttCol(self.positions_dict['att_col'], [], self.database, is_on_focus=False, visible_off_focus=False)
        self.component_dict['att_col'].listen_to(self.component_dict['paper_col'], channel=0)
        self.component_dict['paper_col'].listen_to(self.component_dict['att_col'], channel=0)
        self.component_dict['tree'].listen_to(self.component_dict['paper_col'], channel=0)

        self.component_dict['status_bar'] = Status(self.positions_dict['status_bar'])
        self.component_dict['input_box'] = MyInput(self.positions_dict['input_box'])
        self.component_dict['menu'] = Menu(self.positions_dict['menu'], [])

        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.feed_data()
        self.listen_to(self.component_dict['tree'], 1)
        self.listen_to(self.component_dict['paper_col'], 1)
        self.listen_to(self.component_dict['att_col'], 1)

    def feed_data(self):
        collection_tree = self.database.get_collection()
        self.component_dict['tree'].update(collection_tree)
        current_collection = self.component_dict['tree'].get_current_item()

        papers = self.database.get_list_papers(current_collection)
        self.component_dict['paper_col'].update(papers)
        if len(papers) > 0:
            paper_id = papers[self.component_dict['paper_col'].chosen_ind]['ID']
            attributes = self.database.get_paper_attributes(paper_id)
        else:
            attributes = []
        self.component_dict['att_col'].update(attributes)

    def reload(self):
        self.database.reload()
        self.feed_data()
        self.notify_user('Updated')

    def update_interface_only(self):
        max_nlines, max_ncols = self.stdscr.getmaxyx()
        wide_enlarger = False
        if max_ncols>self.max_ncols:
            wide_enlarger = True
        self.max_nlines = max_nlines
        self.max_ncols = max_ncols

        self.positions_dict = MainApp.get_layout(max_nlines, max_ncols)
        if wide_enlarger:
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
                self.open_bib_file()
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
        # elif c== 27:
        #     # Don't wait for another key
        #     # If it was Alt then curses has already sent the other key
        #     # otherwise -1 is sent (Escape)
        #     stdscr.nodelay(True)
        #     n = stdscr.getch()
        #     if n == -1:
        #         # Escape was pressed
        #         print_me(stdscr, 'escape')
        #         status_bar.clear()
        #     # Return to delay
        #     stdscr.nodelay(False)

        # elif c == ord('m'):
        #     # if menu_visiable:
        #     #     menu.render()
        #     #     menu.get_focus()
        #     #     my_cols[chosen_col].lost_focus()
        #     # else:
        #     #     menu.clear()
        #     #     my_cols[chosen_col].get_focus()
        #     # menu_visiable = not menu_visiable
        #     pass

    def search_on(self):
        self.global_state['paper_col_data'] = self.component_dict['paper_col'].dump()

        current_collection = self.component_dict['tree'].get_current_item()
        papers = self.database.get_list_papers(current_collection)[:2]
        self.component_dict['paper_col'].update(papers)
        self.notify_user('Showing search GUI')

    def search_off(self):
        self.component_dict['paper_col'].recover(self.global_state['paper_col_data'])
        self.notify_user('Back to main GUI')

    def wait_for_command(self):
        self.notify_user(':')
        command_info = dict()
        self.component_dict['input_box'].active()
        command = self.component_dict['input_box'].get()
        if command[:8] == 'download':
            command_info = {'name': 'DOWNLOAD', 'paper_id': self.component_dict['paper_col'].get_current_paper()['ID'], 'url': command[9:].strip()}
        elif command[:10] == 'update_pdf':
            command_info = {'name': 'UPDATE_PDF', 'paper_id': self.component_dict['paper_col'].get_current_paper()['ID'], 'url': command[11:].strip()}
        elif command[:8] == 'copy_bib':
            event = {'name': 'COPY_BIB', 'owner': 'main_app'}
            self.component_dict[self.global_state['current_component']].receive_event(event)
            command_info = {'name': 'SKIP'}
        else:
            command_info = {'name': 'UNDEFINED', 'message': command.strip()}
        return command_info

    def perform_command(self, command_info):
        if command_info['name'] == 'DOWNLOAD':
            self.notify_user('Performing command DOWNLOAD ...')

            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(self.current_path, 'data', 'pdfs', filename)
            if os.path.exists(path_to_file):
                raise Exception('file exists')
            download_file(command_info['url'], path_to_file)
            self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
            self.notify_user('Downloading ... Done')
        if command_info['name'] == 'UPDATE_PDF':
            self.notify_user('Performing command UPDATE_PDF ... Downloading pdf..')

            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(self.current_path, 'data', 'pdfs', filename)
            download_file(command_info['url'], path_to_file)
            self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
            self.notify_user('Downloading ... Done. Updated file')
        elif command_info['name'] == 'UNDEFINED':
            text = 'You entered an undefined command: "%s"' % command_info['message'] # hard code 5
            self.notify_user(text)

    def notify_user(self, message):
        self.component_dict['status_bar'].update(message)


    def open_bib_file(self):
        self.stdscr.refresh()
        curses.def_prog_mode()
        curses.endwin()
        relative_path = 'data/bib_collection.bib'
        current_path = os.path.dirname(os.path.abspath(__file__))
        path_to_file = os.path.join(current_path, relative_path)
        subprocess.check_call(['/usr/bin/vim', '+normal G$', path_to_file])
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


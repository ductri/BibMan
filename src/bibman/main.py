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
import webbrowser

from anytree import Node, PreOrderIter
from anytree.resolver import Resolver, ChildResolverError
import pdf2bib
from pdf2bib import pdf2bib_singlefile

from bibman.utils.data_manager import DatabaseManager
from bibman.utils.network_utils import download_file
from bibman.utils import others
from bibman.base import ScrollableList
from bibman.tree_list import TreeList
from bibman.att_col import AttCol
from bibman.paper_col import PaperCol
from bibman import config



def print_me(screen, msg, ncol=0):
    screen.addstr(0, ncol, msg) # divide by zero


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

class FloatBox(object):
    def __init__(self, pos):
        nlines, ncols, begin_line, begin_col = pos
        self.nlines = nlines
        self.ncols = ncols
        self.win = curses.newwin(nlines, ncols, begin_line, begin_col)

    def update(self, msg):
        self.win.erase()
        # if len(msg) > self.ncols:
        #     msg = msg[:self.ncols-6] +' ...'
        lines = msg.split('\n')
        for i, line in enumerate(lines):
            self.win.addstr(i, 1, line)
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
            elif c == curses.ascii.ESC: # Esc or Alt
                self.text = ''
                break
                # Don't wait for another key
                # If it was Alt then curses has already sent the other key
                # otherwise -1 is sent (Escape)
                # self.win.nodelay(True)
                # n = self.win.getch()
                # if n == -1:
                #     # Return to delay
                #     # self.win.nodelay(False)
                #     self.text = ''
                #     break
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
        att_width = ncols - list_ncols[0] - list_ncols[1]-2*space-2
        list_ncols.append(att_width)

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
        positions_dict['help_box'] = (30, 50, 10, 30)
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
        # stdscr.bkgd(1)

        self.global_state = {'current_component':  'paper_col', 'alternative_gui_visible': False}

        self.max_nlines, self.max_ncols = self.get_size()
        self.positions_dict = MainApp.get_layout(self.max_nlines, self.max_ncols)
        self.component_dict = dict()
        self.component_dict['tree'] = TreeList(self.database, self.positions_dict['tree'])
        self.component_dict['paper_col'] = PaperCol(self.positions_dict['paper_col'], \
                [], self.database, self.notify_user, \
                visible_off_focus=False, is_on_focus=True)
        self.component_dict['paper_col'].listen_to(self.component_dict['tree'], channel=0)
        self.component_dict['att_col'] = AttCol(self.positions_dict['att_col'], None, self.database, is_on_focus=False, visible_off_focus=False)
        self.component_dict['att_col'].listen_to(self.component_dict['paper_col'], channel=0)
        self.component_dict['paper_col'].listen_to(self.component_dict['att_col'], channel=0)
        self.component_dict['tree'].listen_to(self.component_dict['paper_col'], channel=0)

        self.component_dict['status_bar'] = Status(self.positions_dict['status_bar'])
        self.component_dict['input_box'] = MyInput(self.positions_dict['input_box'])
        self.component_dict['menu'] = Menu(self.positions_dict['menu'], [])
        self.component_dict['help_box'] = FloatBox(self.positions_dict['help_box'])

        # self.path_to_data = config.data_dir
        # os.path.dirname(os.path.abspath(__file__))
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
                self.exit()
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
            elif c == ord('0'):
                event = {'name': 'GOTO', 'owner': 'main_app', 'line_number': 0}
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
            elif c == ord('S'):
                self.global_state['alternative_gui_visible'] = not self.global_state['alternative_gui_visible']
                if self.global_state['alternative_gui_visible']:
                    self.search_on()
                else:
                    self.search_off()
            elif c == ord('m'):
                self.notify_user('Waiting for the second key ...')
                c1 = self.component_dict['status_bar'].win.getch()
                if c1 == ord('b'):
                    event = {'name': 'COPY_BIB', 'owner': 'main_app'}
                    self.component_dict[self.global_state['current_component']].receive_event(event)
                    self.notify_user('Received "b". Copied bibtex.')
                else:
                    self.notify_user('')
            elif c == ord(':'):
                command_info = self.wait_for_command()
                self.perform_command(command_info)
            elif c == ord('/'):
                command_info = self.wait_for_command(search=True)
                self.perform_command(command_info)
            elif c == ord(']'):
                event = {'name': 'SHIFT_RIGHT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('['):
                event = {'name': 'SHIFT_LEFT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('B'):
                command_info = {'name': 'ADD_BIB', 'owner': 'main_app'}
                self.perform_command(command_info)
            elif c == ord('K'):
                event = {'name': 'ORDERING_UP', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord('J'):
                event = {'name': 'ORDERING_DOWN', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
            elif c == ord(' '):
                event = {'name': 'TOGGLE_SELECT', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                self.notify_user('') # this is quite a not good hack

    def search_on(self):
        self.global_state['paper_col_data'] = self.component_dict['paper_col'].dump()
        event = {'name': 'NEW_COLLECTION', 'papers': self.searched_papers, 'owner': 'main_app', 'search_result': True}
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
        sep_ind = command.find(' ')
        if sep_ind == -1:
            command_name = command
            command_content = ''
        else:
            command_name = command[:sep_ind]
            command_content = command[sep_ind:]

        if search:
            if command.strip() == '':
                command_info = {'name': 'SKIP'}
            elif command_name == 'title':
                command_info = {'name': 'SEARCH_TITLE', 'key': command_content.strip()}
            else:
                command_info = {'name': 'SEARCH_TITLE', 'key': command.strip()}
        else:
            if len(command) == 0:
                command_info = {'name': 'SKIP'}
            elif command_name == 'download':
                command_info = {'name': 'DOWNLOAD', 'paper_id': \
                    self.component_dict['paper_col'].get_current_paper()['ID'], \
                    'url': command_content.strip()}
            elif command_name == 'update_pdf':
                command_info = {'name': 'UPDATE_PDF', 'paper_id': \
                    self.component_dict['paper_col'].get_current_paper()['ID'],\
                    'url': command_content.strip()}
            elif command_name == 'copy_bib':
                event = {'name': 'COPY_BIB', 'owner': 'main_app'}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command_name == 'add_paper':
                command_info = {'name': 'ADD_PAPER', 'owner': 'main_app', \
                        'title': command_content.strip()}
            elif command_name == 'paper_url':
                command_info = {'name': 'ADD_PAPER_URL', 'owner': 'main_app', \
                        'url': command_content.strip()}
            elif command_name == 'remove_paper':
                command_info = {'name': 'REMOVE_PAPER', 'owner': 'main_app'}
            elif command_name == 'evince':
                command_info = {'name': 'EVINCE', 'owner': 'main_app'}
            elif command_name == 'zathura':
                command_info = {'name': 'ZATHURA', 'owner': 'main_app'}
            elif command_name == 's_title':
                command_info = {'name': 'SEARCH_TITLE', 'key': command_content.strip()}
            elif command_name == 's_author':
                command_info = {'name': 'SEARCH_AUTHOR', 'key': command_content.strip()}
            elif command_name == 'search':
                command_info = {'name': 'SEARCH', 'key': command_content.strip()}
            elif command_name == 'add_local_file':
                command_info = {'name': 'ADD_LOCAL_FILE', 'paper_id': \
                        self.component_dict['paper_col'].get_current_paper()['ID'], \
                        'path': command_content.strip()}
            elif command_name == 'add_tag':
                event = {'name': 'ADD_TAG',  'owner' : 'main_app',  \
                        'tag': command_content.strip()}
                current_component = self.component_dict[self.global_state['current_component']]
                current_component.receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command_name == 'remove_tag':
                event = {'name': 'REMOVE_TAG',  'owner' : 'main_app',  \
                        'tag': command_content.strip()}
                current_component = self.component_dict[self.global_state['current_component']]
                current_component.receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command_name == 'new_child_tag':
                event = {'name': 'NEW_CHILD_TAG', 'owner': 'main_app', \
                        'tag_name': command_content.strip()}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command_name == 'new_sibling_tag':
                event = {'name': 'NEW_SIBLING_TAG', 'owner': 'main_app', \
                        'tag_name': command_content.strip()}
                self.component_dict[self.global_state['current_component']].receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command_name == '?':
                command_info = {'name': 'LIST_COMMANDS', 'owner': 'main_app'}
            elif command_name == 'add_bib':
                command_info = {'name': 'ADD_BIB', 'owner': 'main_app'}
            elif command_name == 'note':
                command_info = {'name': 'OPEN_NOTE', 'owner': 'main_app'}
            elif command_name == 'add_label':
                event = {'name': 'ADD_LABEL', 'owner': 'main_app', \
                        'label': command_content.strip()}
                current_component = self.component_dict[self.global_state['current_component']]
                current_component.receive_event(event)
                command_info = {'name': 'SKIP'}
            elif command_name == 'remove_label':
                event = {'name': 'REMOVE_LABEL',  'owner' : 'main_app',  \
                        'label': command_content.strip()}
                current_component = self.component_dict[self.global_state['current_component']]
                current_component.receive_event(event)
                command_info = {'name': 'SKIP'}
            else:
                command_info = {'name': 'UNDEFINED', 'message': command.strip()}
        return command_info

    def perform_command(self, command_info):
        if command_info['name'] == 'DOWNLOAD':
            self.notify_user('Performing command DOWNLOAD ...')

            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(config.data_dir, 'pdfs', filename)
            if download_file(command_info['url'], path_to_file):
                self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
                self.database.update_paper(paper_id, 'url', command_info['url'])
                self.notify_user('Downloading ... Done')
            else:
                self.notify_user('Downloading ... Failed.')
        elif command_info['name'] == 'ADD_LOCAL_FILE':
            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(config.data_dir, 'pdfs', filename)
            src = command_info['path']
            shutil.copyfile(src, path_to_file)
            self.database.update_paper(paper_id, 'file', os.path.join('pdfs', filename))
            self.notify_user('Added file.')
        elif command_info['name'] == 'UPDATE_PDF':
            self.notify_user('Performing command UPDATE_PDF ... Downloading pdf..')

            paper_id = command_info['paper_id']
            filename = paper_id +'.pdf'
            path_to_file = os.path.join(config.data_dir, 'pdfs', filename)
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
        elif command_info['name'] == 'ADD_BIB':
            content = self.get_text_from_buffer('.tmp_bib')
            if content != '':
                tags = self.component_dict['tree'].get_current_item()
                new_paper = others.rawbib2json(content)
                new_paper['tags'] = tags
                added_paper = self.database.add_paper(new_paper)
                self.update_data()
                self.notify_user('Added paper ID %s' % added_paper['ID'])
            else:
                self.notify_user('Content is empty!')
        elif command_info['name'] == 'ADD_PAPER_URL':
            self.notify_user('Downloading ...')
            url = command_info['url']
            filename = str(random.randint(0, 100000000000))
            path_to_file = os.path.join(config.data_dir, 'pdfs', '%s.pdf'%filename)
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
        elif command_info['name'] == 'ZATHURA':
            event = {'name': 'ZATHURA', 'owner': 'main_app'}
            self.component_dict[self.global_state['current_component']].receive_event(event)
        elif command_info['name'] == 'SEARCH_TITLE':
            self.searched_papers = others.search_title(self.component_dict['paper_col'].get_papers(), command_info['key'])
            self.search_on()
            self.global_state['alternative_gui_visible'] = True
        elif command_info['name'] == 'SEARCH_AUTHOR':
            self.searched_papers = others.search_author(self.component_dict['paper_col'].get_papers(), command_info['key'])
            self.search_on()
            self.global_state['alternative_gui_visible'] = True
        elif command_info['name'] == 'SEARCH':
            self.searched_papers = others.search_all(self.component_dict['paper_col'].get_papers(), command_info['key'])
            self.search_on()
            self.global_state['alternative_gui_visible'] = True
        # elif command_info['name'] == 'ADD_LABEL':
        #     event = {'name': 'ADD_LABEL', 'owner' : 'main_app',  \
        #             'label': command_content.strip()}
        #     current_component = self.component_dict[self.global_state['current_component']]
        #     current_component.receive_event(event)
        #     command_info = {'name': 'SKIP'}
            # paper = self.component_dict['paper_col'].get_current_paper()
            # label = command_info['label']
            # paper_id = paper['ID']
            # self.database.update_paper(paper_id, 'label', label)
            # self.notify_user('Added label "%s" to paper id "%s"'% (label, paper_id))
        elif command_info['name'] == 'LIST_COMMANDS':
            list_commands = self.component_dict[self.global_state['current_component']].get_list_commands()
            self.component_dict['help_box'].update('\n'.join(list_commands))
        elif command_info['name'] == 'OPEN_NOTE':
            event = {'name': 'OPEN_NOTE', 'owner': 'main_app'}
            self.component_dict[self.global_state['current_component']].receive_event(event)

        elif command_info['name'] == 'SKIP':
            pass
        else:
            raise Exception('Command %s is undefined' % command_info['name'])

    def edit_file_with_vim(self, file_path):
        self.stdscr.refresh()
        curses.def_prog_mode()
        curses.endwin()
        # relative_path = config.data_dir= os.path.dirname(os.path.abspath(__file__))
        path_to_file = os.path.join(config.data_dir, file_path)
        subprocess.run(['vim', path_to_file])
        curses.reset_prog_mode()
        self.reload()
        self.stdscr.refresh()

    def open_paper_external(self, path, program='evince'):
        if path.startswith('https'):
            webbrowser.open(path, new=0, autoraise=True)
            self.notify_user('opened url successfully')
        else:
            path_to_file = os.path.join(config.data_dir, path)
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
        path_to_file = os.path.join(config.data_dir, 'bib_collection.bib')
        # path_to_data = os.path.dirname(os.path.abspath(__file__))
        # path_to_file = os.path.join(path_to_data, relative_path)
        subprocess.run(['vim', '-c silent! /%s'%key, path_to_file])
        curses.reset_prog_mode()
        self.reload()
        self.stdscr.refresh()

    def get_text_from_buffer(self, buffer_name):
        self.stdscr.refresh()
        curses.def_prog_mode()
        curses.endwin()
        # relative_path = 'data/%s' % buffer_name
        # path_to_data = os.path.dirname(os.path.abspath(__file__))
        # path_to_file = os.path.join(path_to_data, relative_path)
        path_to_file = os.path.join(config.data_dir, buffer_name)
        subprocess.run(['vim', '-c :set paste', "-c startinsert", path_to_file])
        with open('data/%s' % buffer_name, 'rt') as file_handler:
            text = file_handler.read()
        with open('data/%s' % buffer_name, 'wt') as file_handler:
            file_handler.write('')
        curses.reset_prog_mode()
        self.reload()
        self.stdscr.refresh()
        return text

    def add_listener(self, listener, channel):
        if channel in self.channels:
            self.channels[channel].append(listener)
        else:
            self.channels[channel] = [listener]

    def listen_to(self, host, channel):
        host.add_listener(self, channel)

    def exit(self):
        self.database.exit()

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
            elif event['name'] == 'RESP_ZATHURA':
                self.open_paper_external(event['relative_path'], program='zathura')
            elif event['name'] == 'RESP_OPEN_NOTE':
                self.edit_file_with_vim(event['relative_path'])
        elif event['owner'] == 'att_col':
            if event['name'] == 'LOST_FOCUS':
                self.global_state['current_component'] = 'paper_col'
            elif event['name'] == 'COPY_TO_CLIPBOARD':
                self.notify_user('Text is sent to clipboard')


def main(stdscr):
    stdscr = curses.initscr()

    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK) # For search
    stdscr.bkgd(curses.color_pair(1))

    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    app = MainApp(stdscr)
    app.run()


def run():
    wrapper(main)


if __name__ == "__main__":
    wrapper(main)


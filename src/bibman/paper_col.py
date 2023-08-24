import curses
from datetime import datetime
import pyperclip

from bibman.base import ScrollableList
from bibman.utils.data_manager import DatabaseManager
from bibman.utils import others


class PaperCol(ScrollableList):
    def __init__(self, pos, papers, database, notify_user, \
            visible_off_focus=False, is_on_focus=False):
        self.__papers = papers # todo maybe we dont need this much info
        self.database = database
        self.notify_user = notify_user
        self.deco_type = 'INDEX'
        items = self.papers2strs(self.__papers, deco_type=self.deco_type)
        ScrollableList.__init__(self, pos, items, visible_off_focus=visible_off_focus, is_on_focus=is_on_focus)

    def __set_papers(self, papers):
        self.__papers = sorted(papers, \
                key=lambda p: (float(p['__order_value']), datetime.strptime(p['created_time'], DatabaseManager.DATETIME_FORMAT)),\
                reverse=True
                )

    def papers2strs(self, papers, deco_type='SIMPLE'):
        deco_title = lambda paper: (f"[{','.join(sorted(list(paper['label'])))}] " if len(paper['label']) !=0 else '') + paper['title']
        if deco_type == 'SIMPLE':
            return ['> '+ deco_title(paper) for paper in papers]
        elif deco_type == 'INDEX':
            return [f'{i}. '+deco_title(paper) for i, paper in enumerate(papers)]
        elif deco_type == 'EMPTY':
            return [deco_title(paper) for paper in papers]
        else:
            raise Exception(f'Unsupported deco_type of {deco_type}')

    def get_papers(self):
        return self.__papers
    def get_bib(self):
        return others.export_bib_format(self.get_current_paper())
    def get_current_paper(self):
        if len(self.__papers) > 0:
            return self.__papers[self.get_single_chosen_item()]
        else:
            return None
    def get_upper_paper(self):
        return self.__papers[max(self.get_single_chosen_item()-1, 0)]
    def get_lower_paper(self):
        return self.__papers[min(self.get_single_chosen_item()+1, len(self.__papers)-1)]

    def lost_focus(self, direction):
        ScrollableList.lost_focus(self)
        event = {'name': 'LOST_FOCUS', 'owner': 'paper_col', 'direction': direction}
        self.broadcast(event, 0)
        self.broadcast(event, 1)

    def broadcast_new_paper(self):
        if len(self.__papers)>0:
            event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper': self.get_current_paper()}
        else:
            event = {'name': 'NEW_PAPER', 'owner': 'paper_col', 'paper': None}
        self.broadcast(event, 0)

    def broadcast_request_update(self):
        event = {'name': 'UPDATE_PAPER', 'owner': 'paper_col', 'paper': self.get_current_paper()}
        self.broadcast(event, 0)

    def select_next(self):
        ScrollableList.select_next(self)
        self.broadcast_new_paper()

    def select_previous(self):
        ScrollableList.select_previous(self)
        self.broadcast_new_paper()

    def move_item_up(self):
        current_paper = self.get_current_paper()
        current_paper_order_value = current_paper['__order_value']
        upper_paper = self.get_upper_paper()
        upper_paper_order_value = upper_paper['__order_value']
        current_paper['__order_value'] = upper_paper_order_value
        upper_paper['__order_value'] = current_paper_order_value
        # Currently, this operation of updating database takes some time
        # So the trick is only update database on memory. This would rely on user to press update to perform a database dumping to disk.
        self.database.update_batch_paper([current_paper['ID'], upper_paper['ID']], '__order_value', [current_paper['__order_value'], upper_paper['__order_value']], only_on_memory=True)
        self.update(self.get_papers())
        self.select_previous()

    def move_item_down(self):
        current_paper = self.get_current_paper()
        current_paper_order_value = current_paper['__order_value']
        lower_paper = self.get_lower_paper()
        lower_paper_order_value = lower_paper['__order_value']
        current_paper['__order_value'] = lower_paper_order_value
        lower_paper['__order_value'] = current_paper_order_value
        # Currently, this operation of updating database takes some time
        # So the trick is only update database on memory. This would rely on user to press update to perform a database dumping to disk.
        self.database.update_batch_paper([current_paper['ID'], lower_paper['ID']], '__order_value', [current_paper['__order_value'], lower_paper['__order_value']], only_on_memory=True)
        self.update(self.get_papers())
        self.select_next()

    def goto(self, line_number):
        ScrollableList.goto(self, line_number)
        self.broadcast_new_paper()

    def update(self, papers):
        self.__set_papers(papers)
        items = self.papers2strs(self.__papers, deco_type=self.deco_type)
        ScrollableList.update(self, items, chosen_ind=self.get_single_chosen_item(), start_index=self.start_index)


    def dump(self):
        data = ScrollableList.dump(self)
        data['papers'] = self.__papers
        data['database'] = self.database
        return data

    def recover(self, data):
        self.__set_papers(data['papers'])
        self.database = data['database']
        ScrollableList.recover(self, data)

    def get_list_commands(self):
        """ for help"""
        return ['**** COMMANDS **** ', \
                '- `add_paper` paper_name', \
                '- `remove`', \
                '- `add_bib`', \
                '- `s_author`', \
                '- `s_title`', \
                '- `search`', \
                '- `add_tag` tag_name', \
                '- `remove_tag` tag_name', \
                '- `add_label` label_name', \
                '', \
                '**** SHORT KEYS ****', \
                '- KEY B: add_bib', \
                '- KEY mb: copy_bib', \
                '- KEY K: move the current item up', \
                ]

    def add_tag(self, event):
        papers = [self.__papers[i] for i in self.get_active_inds()]
        paper_ids = [paper['ID'] for paper in papers]
        tag = event['tag']
        new_tags = [paper['tags'] | set([tag]) for paper in papers]
        self.database.update_batch_paper(paper_ids, 'tags', new_tags)

        paper_ids_str = str(paper_ids[0])
        if len(paper_ids) == 1:
            self.notify_user(f'Added tag "{tag}" to paper [{paper_ids_str}]')
        else:
            self.notify_user(f'Added tag "{tag}" to {len(paper_ids)} papers, including [{paper_ids_str}], and so on')

    def remove_tag(self, event):
        papers = [self.__papers[i] for i in self.get_active_inds()]
        paper_ids = [paper['ID'] for paper in papers]
        tag = event['tag']
        new_tags = [paper['tags'] - set([tag]) for paper in papers]
        self.database.update_batch_paper(paper_ids, 'tags', new_tags)

        paper_ids_str = str(paper_ids[0])
        if len(paper_ids) == 1:
            self.notify_user(f'Removed tag "{tag}" from paper [{paper_ids_str}]. Interface is NOT updated')
        else:
            self.notify_user(f'Removed tag "{tag}" from {len(paper_ids)} papers, including [{paper_ids_str}], and so on. Interface is NOT updated')

    def add_label(self, event):
        papers = [self.__papers[i] for i in self.get_active_inds()]
        paper_ids = [paper['ID'] for paper in papers]
        new_labels = [paper['label'] | set([event['label']]) for paper in papers]
        self.database.update_batch_paper(paper_ids, 'label', new_labels)

        paper_ids_str = str(paper_ids[0])
        label = event['label']
        if len(paper_ids) == 1:
            self.notify_user(f'Added label "{label}" to paper [{paper_ids_str}]')
        else:
            self.notify_user(f'Added label "{label}" to {len(paper_ids)} papers, including [{paper_ids_str}], and so on')

    def remove_label(self, event):
        papers = [self.__papers[i] for i in self.get_active_inds()]
        paper_ids = [paper['ID'] for paper in papers]
        label = event['label']
        new_label = [paper['label'] - set([label]) for paper in papers]
        self.database.update_batch_paper(paper_ids, 'label', new_label)

        paper_ids_str = str(paper_ids[0])
        if len(paper_ids) == 1:
            self.notify_user(f'Removed label "{label}" from paper [{paper_ids_str}]. Interface is NOT updated')
        else:
            self.notify_user(f'Removed label "{label}" from {len(paper_ids)} papers, including [{paper_ids_str}], and so on. Interface is NOT updated')

    def receive_event(self, event):
        if event['owner'] == 'main_app':
            if event['name'] == 'UPDATE_COLLECTION':
                self.update(event['papers'])
                self.start_index(0)
            elif event['name'] == 'NEW_COLLECTION':
                if 'search_result' in event.keys() and event['search_result']:
                    self.win.bkgd(curses.color_pair(3))
                else:
                    self.win.bkgd(curses.color_pair(ScrollableList.DEFAULT_COLOR))

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
                relative_path = self.get_current_paper()['file']
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
                event = {'name': 'ASK_OPEN_BIB', 'paper_id': self.get_current_paper()['ID'], 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'REMOVE_PAPER':
                event = {'name': 'RESP_REMOVE_PAPER', 'paper_id': self.get_current_paper()['ID'], 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'EVINCE':
                event = {'name': 'RESP_EVINCE', 'relative_path': self.get_current_paper()['file'], 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'ZATHURA':
                event = {'name': 'RESP_ZATHURA', 'relative_path': self.get_current_paper()['file'], 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'OPEN_NOTE':
                event = {'name': 'RESP_OPEN_NOTE', 'relative_path': self.get_current_paper()['ID']+'_note', 'owner': 'paper_col'}
                self.broadcast(event, 1)
            elif event['name'] == 'ORDERING_UP':
                self.move_item_up()
            elif event['name'] == 'ORDERING_DOWN':
                self.move_item_down()
            elif event['name'] == 'TOGGLE_SELECT':
                self.toggle_select()
            elif event['name'] == 'ADD_TAG':
                self.add_tag(event)
            elif event['name'] == 'REMOVE_TAG':
                self.remove_tag(event)
            elif event['name'] == 'ADD_LABEL':
                self.add_label(event)
            elif event['name'] == 'REMOVE_LABEL':
                self.remove_label(event)
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


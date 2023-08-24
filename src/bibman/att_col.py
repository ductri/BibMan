import pyperclip

from bibman.base import ScrollableList


class AttCol(ScrollableList):
    ATTRIBUTES = [('title', 'Title: '), ('author','Authors: '), ('year', 'Year: '), ('journal', 'Venue: '), ('created_time',  'Created: ')]
    def __init__(self, pos, paper, database, visible_off_focus=True, is_on_focus=False):
        self.database = database
        if paper:
            self.atts = AttCol.get_paper_attributes(paper)
        else:
            self.atts = []
        items = self.add_decoration(self.atts)
        ScrollableList.__init__(self, pos, items, visible_off_focus=visible_off_focus, is_on_focus=is_on_focus, wrap=True)
        self.min_width = 6

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
            assert any([len(line)<=step+2 for line in lines])
            return lines

        def author2lines(author_str):
            max_lines = 4
            lines = [' - ' + author.strip() for author in author_str.split(' and ')]
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
                # lines = ['P', '  lan afte', '  r submis', '  sion', '']
                # lines = ['a', ' b', ' c', ' d', '']
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
                max_lines = 4
                if len(lines) > max_lines:
                    lines = lines[:max_lines-1] + ['   ...']
                else:
                    lines = lines + ['']*(max_lines - len(lines))
                lines = [head] + lines +['']
                results.append(attr_name + '\n'.join(lines))
            else:
                results.append(attr_name + attr_value + '\n')
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
                pyperclip.copy(self.atts[self.get_single_chosen_item()])
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
        ScrollableList.update(self, items, chosen_ind=self.get_single_chosen_item(), start_index=self.start_index)


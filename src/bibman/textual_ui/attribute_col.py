from typing import List
from typing_extensions import Self
from inspect import Attribute

from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive

from .my_list_view import MyListView
from .observer_dp import MyEvent, Subscriber, Publisher



class AttributeController(Publisher):
    ATTRIBUTES = (('title', 'Title: '), ('author','Authors: '), ('year', 'Year: '), ('journal', 'Venue: '), ('created_time',  'Created: '))

    def __init__(self):
        super().__init__()
        self.atts = []

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, Controller):
            if event.name == 'choose_paper':
                paper = event.data['paper']
                self.atts = self.get_paper_attributes(paper)

    def render(self):
        def add_decoration(attr_values, ncols):
            def title2lines(title, ncols):
                max_lines = 4
                head_len = max(ncols-10, 0)
                head = title[:head_len]
                tail = title[head_len:]
                step = ncols - 3
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
            for ((attr_key, attr_name), attr_value) in zip(AttributeController.ATTRIBUTES, attr_values):
                if attr_key == 'created_time':
                    results.append(attr_name + '\n    ' + attr_value)
                elif attr_key == 'title':
                    lines = title2lines(attr_value, ncols)
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'author':
                    lines = author2lines(attr_value)
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'year':
                    lines = [attr_value, '']
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'booktitle':
                    head_len = max(ncols-10, 0)
                    head = attr_value[:head_len]
                    tail = attr_value[head_len:]
                    step = ncols - 3
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
        items = add_decoration(self.atts, 50)
        print('\n'.join(items))

    def get_paper_attributes(self, paper):
        if paper:
            return [paper[item[0]] for item in AttributeController.ATTRIBUTES]
        else:
            return []

    def update_new_data(self, paper):
        self.paper = paper


class AttributeColumn(Static):
    """
    - To render and to receive user input
    - It is stateless in terms of data, only stateful in terms of UI
    """

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ]
    data = reactive([
                ('Paper 5 '),
                ('Paper 10'),
                ('Paper 100')
                ])
    def __init__(self):
        super().__init__()
        self.view = MyListView()
        self.controller = AttributeController()

    # def inject_data(self, data: List[str]):
    #     self.data = data

    def compose(self) -> ComposeResult:
        # data = [ListItem(Label(item)) for item in self.data]
        # yield MyListView(*data)
        yield self.view

    def focus(self, scroll_visible: bool = True) -> Self:
        self.view.focus()
        return self

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_remove_item(self):
        self.data.remove(self.data[0])

    def ui_update_new_data(self, paper):
        def add_decoration(attr_values, ncols):
            def title2lines(title, ncols):
                max_lines = 4
                head_len = max(ncols-10, 0)
                head = title[:head_len]
                tail = title[head_len:]
                step = ncols - 3
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
            for ((attr_key, attr_name), attr_value) in zip(AttributeController.ATTRIBUTES, attr_values):
                if attr_key == 'created_time':
                    results.append(attr_name + '\n    ' + attr_value)
                elif attr_key == 'title':
                    lines = title2lines(attr_value, ncols)
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'author':
                    lines = author2lines(attr_value)
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'year':
                    lines = [attr_value, '']
                    results.append(attr_name + '\n'.join(lines))
                elif attr_key == 'booktitle':
                    head_len = max(ncols-10, 0)
                    head = attr_value[:head_len]
                    tail = attr_value[head_len:]
                    step = ncols - 3
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
                return [paper[item[0]] for item in AttributeController.ATTRIBUTES]
            else:
                return []

        attrs = get_paper_attributes(paper)
        items = add_decoration(attrs, 50)
        items = [ListItem(Label(item)) for item in items]
        self.view.clear()
        self.view.extend(items)

    def update_new_data(self, paper):
        self.controller.update_new_data(paper)
        self.ui_update_new_data(paper)
        self.view.index = 0



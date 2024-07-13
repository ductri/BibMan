from typing import List, Dict
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive
from typing_extensions import Self
from textual.message import Message

from .my_list_view import MyListView
from .tag_col import GivingUpFocus
from .observer_dp import MyEvent, Subscriber, Publisher


class PaperController(Publisher):
    def __init__(self):
        super().__init__()
        self.papers = [] # todo maybe we dont need this much info
        self.deco_type = 'INDEX'

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, Controller):
            if event.name == 'choose_tags':
                self.papers = event.data['papers']
                if len(self.papers) > 0:
                    self.action_choose_paper(0)

    def render(self):
        def papers2strs(papers, deco_type='SIMPLE'):
            deco_title = lambda paper: (f"[{','.join(sorted(list(paper['label'])))}] " if len(paper['label']) !=0 else '') + paper['title']
            if deco_type == 'SIMPLE':
                return ['> '+ deco_title(paper) for paper in papers]
            elif deco_type == 'INDEX':
                return [f'{i}. '+deco_title(paper) for i, paper in enumerate(papers)]
            elif deco_type == 'EMPTY':
                return [deco_title(paper) for paper in papers]
            else:
                raise Exception(f'Unsupported deco_type of {deco_type}')

        items = papers2strs(self.papers, deco_type=self.deco_type)
        print('\n'.join (items))

    def my_action_choose_paper(self, paper):
        event = MyEvent(name='choose_paper', data={'paper': paper}, source=self)
        self.notify_event(event)

    def action_choose_paper(self, index):
        self.my_action_choose_paper(self.papers[index])

    def update_new_data(self, papers):
        self.papers = papers


class PaperColumn(Static):
    """
    - To render and to receive user input
    - It is stateless in terms of data, only stateful in terms of UI
    """
    class PaperSelection(Message):
        def __init__(self, paper):
            self.paper = paper
            super().__init__()

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ('r',  'remove_item',  'remove item'),
                ('l', 'move_right', 'Move right'),
                ]

    def __init__(self):
        super().__init__()
        self.__view = MyListView()
        self.deco_type = 'INDEX'
        self.controller = PaperController()

    def compose(self) -> ComposeResult:
        yield self.__view

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_remove_item(self):
        self.__view.pop()

    # # The followings are public API to clients
    # def inject_data(self, data: List[str]):
    #     self.data = data
    #     data_ = [ListItem(Label(item)) for item in data]
    #     self.__view = MyListView(*data_)

    def add_paper(self, paper):
        pass

    def focus(self, scroll_visible: bool = True) -> Self:
        self.__view.focus()
        return self

    def action_move_right(self) -> None:
        self.__view.blur()
        self.post_message(GivingUpFocus('from_paper'))

    def action_select_paper(self, index):
        paper = self.controller.papers[index]
        self.post_message(PaperColumn.PaperSelection(paper))

    def ui_update_new_data(self, papers):
        def papers2strs(papers, deco_type='SIMPLE'):
            deco_title = lambda paper: (f"[{','.join(sorted(list(paper['label'])))}] " if len(paper['label']) !=0 else '') + paper['title']
            if deco_type == 'SIMPLE':
                return ['> '+ deco_title(paper) for paper in papers]
            elif deco_type == 'INDEX':
                return [f'{i}. '+deco_title(paper) for i, paper in enumerate(papers)]
            elif deco_type == 'EMPTY':
                return [deco_title(paper) for paper in papers]
            else:
                raise Exception(f'Unsupported deco_type of {deco_type}')
        items = papers2strs(self.controller.papers, deco_type=self.deco_type)
        items = [ListItem(Label(item)) for item in items]
        self.__view.clear()
        self.__view.extend(items)

    def update_new_data(self, papers: List[Dict]):
        self.controller.update_new_data(papers)
        self.ui_update_new_data(papers)
        self.action_select_paper(0)



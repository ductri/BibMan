from typing import List
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive
from textual.message import Message

from .my_list_view import MyListView




class TagColumn(Static):
    class GivingUpFocus(Message):
        def __init__(self):
            super().__init__()
            self.message = 'giving up focus'
            self.from_col = 'tag_col'

    BINDINGS = [
            ('l', 'move_right', 'Move right'),
            ]
    data = reactive([
                ('tag 1'),
                ('tag 2 10'),
                ('tag 100')
                ])

    def inject_data(self, data: List[str]):
        self.data = data
        data_ = [ListItem(Label(item)) for item in data]
        self.view = MyListView(*data_)

    def compose(self) -> ComposeResult:
        yield self.view

    def action_move_right(self) -> None:
        self.view.blur()
        self.post_message(self.GivingUpFocus())




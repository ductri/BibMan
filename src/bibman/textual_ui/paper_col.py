from typing import List
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive
from typing_extensions import Self

from .my_list_view import MyListView




class PaperColumn(Static):
    """This plays as a bridge between main controller and the paper list UI"""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ( 'r',  'remove_item',  'remove item')
                ]


    def compose(self) -> ComposeResult:
        yield self.__view

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_remove_item(self):
        self.__view.pop()

    # The followings are public API to clients
    def inject_data(self, data: List[str]):
        self.data = data
        data_ = [ListItem(Label(item)) for item in data]
        self.__view = MyListView(*data_)

    def add_paper(self, paper):
        pass

    def focus(self, scroll_visible: bool = True) -> Self:
        self.__view.focus()
        return self



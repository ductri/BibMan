from typing import List
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive
from typing_extensions import Self

from .my_list_view import MyListView


class BaseColumn(Static):
    """This plays as a bridge between main controller and the paper list UI"""

    BINDINGS = []
    def __init__(self, view, data):
        self.__view = view
        self.__data = data

    def compose(self) -> ComposeResult:
        yield self.__view

    def focus(self, scroll_visible: bool = True) -> Self:
        self.__view.focus()
        return self



from typing import List
from textual.app import App, ComposeResult
from textual.reactive import Reactive
from textual.widgets import Header, Footer, ListItem, ListView, Label, Static
from textual.reactive import reactive

from .my_list_view import MyListView



class AttributeColumn(Static):
    """A Textual app to manage stopwatches."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ]
    data = reactive([
                ('Paper 5 '),
                ('Paper 10'),
                ('Paper 100')
                ])

    def inject_data(self, data: List[str]):
        self.data = data

    def compose(self) -> ComposeResult:
        data = [ListItem(Label(item)) for item in self.data]
        yield MyListView(*data)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_remove_item(self):
        self.data.remove(self.data[0])




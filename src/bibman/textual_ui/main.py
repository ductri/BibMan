from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListItem, ListView, Label

from .paper_col import PaperColumn
from .my_list_view import MyListView
from .attribute_col import AttributeColumn
from .tag_col import TagColumn



class BibManApp(App):
    """A Textual app to manage stopwatches."""

    BINDINGS = [('l', 'right', 'Move right'),
                ('h', 'left', 'Move left'),
                ]
    CSS_PATH = "css/bib_man_app.tcss"

    def __init__(self):
        super().__init__()
        self.focus = 0

        self.footer = Footer()
        self.tag_col = self.init_tag_column()
        self.paper_col = self.init_paper_column()
        self.attribute_col = self.init_attribute_column()

    def init_tag_column(self):
        text_data = [
                ('Tag1'),
                ('#100'),
                ('tag 3')
                ]
        tag_col = TagColumn()
        tag_col.inject_data(text_data)
        return tag_col

    def init_paper_column(self):
        text_data = [
                ('Paper #1'),
                ('Paper #100'),
                ('Paper #189')
                ]
        paper_col = PaperColumn()
        paper_col.inject_data(text_data)
        return paper_col

    def init_attribute_column(self):
        text_data = [
                ('Title: Diffusion is all you need'),
                ('Authors: a \n b \n c'),
                ('Year:  2015')
                ]
        attribute_col = AttributeColumn()
        attribute_col.inject_data(text_data)
        return attribute_col

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield self.footer
        yield self.tag_col
        yield self.paper_col
        yield self.attribute_col

    def on_tag_column_giving_up_focus(self, event):
        self.paper_col.focus()


if __name__ == "__main__":
    app = BibManApp()
    app.run()


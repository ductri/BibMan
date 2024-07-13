from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListItem, ListView, Label
from textual import log

from bibman.textual_ui.paper_col import PaperColumn
from bibman.textual_ui.my_list_view import MyListView
from bibman.textual_ui.attribute_col import AttributeColumn
from bibman.textual_ui.tag_col import TagColumn
from bibman.textual_ui.controllers import Controller



class BibManApp(App):
    """A Textual app to manage stopwatches."""

    BINDINGS = [('l', 'go_right', 'Move right'),
                ('h', 'go_left', 'Move left'),
                ('x', 'enter', 'Enter'),
                ]
    CSS_PATH = "css/bib_man_app.tcss"

    def __init__(self):
        super().__init__()
        self.controller = Controller()

        self.footer = Footer()
        # self.tag_col = self.init_tag_column()
        # self.paper_col = self.init_paper_column()
        # self.attribute_col = self.init_attribute_column()

    # def init_tag_column(self):
    #     tag_col = TagColumn()
    #     tag_col.inject_data(self.controller.tag_clt.render())
    #     return tag_col
    #
    # def init_paper_column(self):
    #     text_data = [
    #             ('Paper #1'),
    #             ('Paper #100'),
    #             ('Paper #189')
    #             ]
    #     paper_col = PaperColumn()
    #     paper_col.inject_data(text_data)
    #     return paper_col
    #
    # def init_attribute_column(self):
    #     text_data = [
    #             ('Title: Diffusion is all you need'),
    #             ('Authors: a \n b \n c'),
    #             ('Year:  2015')
    #             ]
    #     attribute_col = AttributeColumn()
    #     attribute_col.inject_data(text_data)
    #     return attribute_col

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield self.footer
        yield self.controller.tag_col
        yield self.controller.paper_col
        yield self.controller.attribute_col

    # def action_enter(self):
    #     if self.controller.focus_column == 'tag_col':
    #         self.controller.tag_clt.action_choose_tag(self.tag_col.view.index)

    # def on_giving_up_focus(self, event):
    #     # self.attribute_col.focus()
    #     # if event.from_col == 'from_tag':
    #     #     self.paper_col.focus()
    #     if event.from_col == 'from_paper':
    #         self.attribute_col.focus()
    #         event.stop()

    def action_go_right(self):
        if self.focused == self.controller.tag_col.view:
            self.controller.paper_col.focus()
        elif self.focused == self.controller.paper_col.view:
            self.controller.attribute_col.focus()
    def action_go_left(self):
        if self.focused == self.controller.attribute_col.view:
            self.controller.paper_col.focus()
        elif self.focused == self.controller.paper_col.view:
            self.controller.tag_col.focus()

    def on_mount(self):
        self.controller.tag_col.update_new_data(self.controller.database.get_collection())
        self.controller.tag_col.focus()

    def on_tag_column_tags_selection(self, event):
        papers = self.controller.database.get_list_papers(event.tags)
        self.controller.paper_col.update_new_data(papers)
        print(event)

    def on_paper_column_paper_selection(self, event):
        paper = event.paper
        self.controller.attribute_col.update_new_data(paper)
        print(event)


if __name__ == "__main__":
    app = BibManApp()
    app.run()


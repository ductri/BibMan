from bibman.textual_ui.tag_col import TagColumn
from bibman.textual_ui.paper_col import PaperColumn
from bibman.textual_ui.attribute_col import AttributeColumn
from bibman.utils.data_manager import DatabaseManager
from anytree import ContRoundStyle, Node, PreOrderIter

from bibman.utils import others
from bibman.textual_ui.observer_dp import MyEvent, Subscriber, Publisher



class Controller(Publisher):
    def __init__(self):
        super().__init__()
        self.database = DatabaseManager()

        # self.tag_clt = TagController(self.database.get_collection(), TagColumn())
        # self.tag_clt.add_listener(self)
        self.tag_col = TagColumn()
        self.tag_col.controller.add_listener(self)

        # self.paper_clt = PaperController(PaperColumn())
        self.paper_col = PaperColumn()

        self.paper_col.controller.add_listener(self)
        self.add_listener(self.paper_col.controller)

        # self.attribute_clt = AttributeController(AttributeColumn())
        self.attribute_col = AttributeColumn()
        self.add_listener(self.attribute_col.controller)

        self.database.add_listener(self.tag_col.controller)

        self.focus_column = 'tag_col'

    def publisher_new_state(self, event: MyEvent):
        if isinstance(event.source, TagController):
            if event.name == 'new_tag':
                tag_name = event.data['tag_name']
                path_to_parent = event.data['path_to_parent']
                self.database.add_new_tag(tag_name, path_to_parent)
            elif event.name == 'choose_tags':
                tags = event.data['tags']
                papers = self.database.get_list_papers(tags)
                event = MyEvent(name='choose_tags', data={'papers': papers}, source=self)
                self.notify_event(event)
        elif isinstance(event.source, PaperController):
            if event.name == 'choose_paper':
                event.source = self
                self.notify_event(event)





if __name__ == "__main__":

    controller = Controller()

    print('---------------- Test 1 ----------- \n')
    controller.tag_clt.my_action_expand(2)
    controller.tag_clt.render()

    print('---------------- Test 2 ----------- \n')
    controller.tag_clt.my_action_add_new_tag('new_tag', controller.tag_clt.flattened_nodes[1])
    controller.tag_clt.my_action_expand(1)
    controller.tag_clt.my_action_add_new_tag('new_tag2', controller.tag_clt.flattened_nodes[5])
    controller.tag_clt.render()

    print('---------------- Test 3 ----------- \n')
    controller.tag_clt.action_choose_tag(12)
    controller.paper_clt.render()

    print('---------------- Test 4 ----------- \n')
    controller.tag_clt.action_choose_tag(17)
    controller.paper_clt.render()

    print('---------------- Test 5 ----------- \n')
    controller.tag_clt.action_choose_tag(12)
    controller.paper_clt.action_choose_paper(-1)
    controller.attribute_clt.render()


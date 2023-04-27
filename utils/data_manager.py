import threading
from time import sleep
import json
from tqdm import tqdm
import bibtexparser
import shutil
import os
import random
from datetime import datetime

from bibtexparser.bibdatabase import BibDatabase


class DatabaseManager(object):
    """
    Next step: eliminate dependence on this poor Bibtexparser
    - Create a Singleton of this class
    *** WARNING ****: potiential bug if creating multiple instances
    """

    DEFAULT_ITEM = {'title': '',  'author': '', 'year': '', 'journal': '', \
            'file': '', 'booktitle': '', 'tags': ',', 'pages':  '', \
            'volume': '', 'created_time': '01/01/1994 00:00:00', \
            '__order_value': '10000000', 'label': ''}
    DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'
    def __init__(self):
        self.current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        with open('./data/collection_tree.txt', 'rt') as file_handler:
            self.collection_tree = json.load(file_handler)
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            bib_database = bibtexparser.load(bibfile)
        self.papers = DatabaseManager.preprocessing(bib_database.entries)
        self.__debt = 0

        # self.__timer = threading.Timer(1.0, self.debt_monitoring)
        # self.__timer.start()

    # def debt_monitoring(self):
    #     self.__debt += 1
    #     if self.__debt > 20:
    #         self.dump()
    #         self.reload()
    #         self.__debt = 0
    #     self.__timer = threading.Timer(1.0, self.debt_monitoring)
    #     self.__timer.start()


    def preprocessing(papers):
        result = []
        for paper in papers:
            new_paper = paper.copy()
            # default_item = {'title': '',  'author': '', 'year': '', 'journal': '', 'file': '', 'booktitle': '', 'tags': ','}
            default_item = DatabaseManager.DEFAULT_ITEM.copy()
            if 'tags' in new_paper.keys():
                new_paper['tags'] = set([item.strip() for item in paper['tags'].split(',')])
            default_item.update(new_paper)
            result.append(default_item)
        return result
    def post_preprocess(papers):
        """
        You better raise Exception here if there's any thing suspicious
        """
        for i in range(len(papers)):
            tags = papers[i]['tags']
            if isinstance(tags, list) or isinstance(tags, set):
                tags = list(tags)
                tags.sort()
                papers[i]['tags'] = ','.join(tags)
            elif isinstance(tags, str):
                papers[i]['tags'] = tags
            else:
                raise Exception('Unknow datatype of tags: %s' % str(type(tags)))

        for paper in papers:
            for k, v in paper.items():
                if not isinstance(v, str):
                    raise Exception('Paper id: %s: Expect field "%s:%s" to be string' %  (paper['ID'], k, str(v)))
        return papers

    def get_collection(self):
        return self.collection_tree

    def get_list_papers(self, tags, neg_tags=set()):
        tags = set(tags)
        result = [paper for paper in self.papers if tags.issubset(paper['tags'])]
        if neg_tags:
            result = [paper for paper in result if not neg_tags.issubset(paper['tags'])]
        return result

    def reload(self):
        if self.__debt>0:
            self.dump()
            self.__debt = 0
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            bib_database = bibtexparser.load(bibfile)
        self.papers = DatabaseManager.preprocessing(bib_database.entries)

    def update_paper(self, paper_id, key, value):
        self.reload()
        for ind, paper in enumerate(self.papers):
            if paper['ID'] == paper_id:
                paper[key] = value

        self.dump()
        self.reload()

    def update_batch_paper(self, list_paper_ids, key, list_values, only_on_memory=False):
        """
        ********  WARNING  *******
        Haven't test it yet
        """
        if only_on_memory:
            all_keys = [paper['ID'] for paper in self.papers]
            for paper_id, value in zip(list_paper_ids, list_values):
                self.papers[all_keys.index(paper_id)][key] = value
                self.__debt += 1
        else:
            self.reload()
            all_keys = [paper['ID'] for paper in self.papers]
            for paper_id, value in zip(list_paper_ids, list_values):
                self.papers[all_keys.index(paper_id)][key] = value
            self.dump()
            self.reload()

    def dump(self):
        """
        DANGEROUS
        """
        self.dump_bib()
        self.dump_collection_tree()

    def dump_bib(self):
        """
        DANGEROUS
        """
        src = os.path.join(self.current_path, 'data', 'bib_collection.bib')
        dst = os.path.join(self.current_path, 'data', '.bib_collection.bib')
        shutil.copyfile(src, dst)

        bib_database = BibDatabase()
        bib_database.entries = DatabaseManager.post_preprocess(self.papers)
        with open(src, 'wt') as bibtex_file:
            bibtexparser.dump(bib_database, bibtex_file)

    def dump_collection_tree(self):
        """
        DANGEROUS
        """
        src = os.path.join(self.current_path, 'data', 'collection_tree.txt')
        dst = os.path.join(self.current_path, 'data', '.collection_tree.txt')
        shutil.copyfile(src, dst)

        with open(src, 'wt') as file_handler:
            json.dump(self.collection_tree, file_handler)

    def _look_paper_up(self, paper_id):
        for paper in self.papers:
            if paper['ID'] == paper_id:
                return paper

    def add_paper(self, paper_info):
        def exists(key, papers):
            return key in [p['ID'] for p in papers]
        default_item = DatabaseManager.DEFAULT_ITEM.copy()
        default_item['ID'] = str(random.randint(0, 100000000000))
        default_item['ENTRYTYPE'] = 'inproceedings'
        default_item.update(paper_info)
        now = datetime.now()
        default_item['created_time'] = now.strftime(DatabaseManager.DATETIME_FORMAT)
        current_order_value = max([float(paper['__order_value']) for paper in self.papers]+[0])
        if current_order_value > 10000000:
            raise Exception('Something wrong must have happened. order value is exceeding 10000000!!!')
        default_item['__order_value'] = str(current_order_value+1+random.uniform(0.00001, 0.99999))
        if not exists(default_item['ID'], self.papers):
            self.papers.append(default_item)
        else:
            raise Exception(f"Paper with id {default_item['ID']} exists")

        self.dump()
        self.reload()
        return default_item

    def remove_paper(self, paper_id):
        paper = self._look_paper_up(paper_id)
        self.papers.remove(paper)
        self.dump()
        self.reload()

    def add_new_tag(self, tag_name, path_to_parent=''):
        current_node = self.collection_tree
        for node in path_to_parent.split('/')[1:]:
            current_node = current_node[node]
        current_node[tag_name] = {}
        self.dump_collection_tree()

    def exit(self):
        # print('Killing timer ...')
        # self.__timer.cancel()
        pass


if __name__ == "__main__":
    import others
    db = DatabaseManager()
    # db.update_paper('test', 'file', 'filefile')
    db.dump()
    # db.get_paper_attributes('test')
    # print(others.export_bib_format(db.bib_database.entries[0]))

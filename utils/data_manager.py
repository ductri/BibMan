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
    VERY BUGGY.
    Next step: eliminate dependence on this poor Bibtexparser
    """

    DEFAULT_ITEM = {'title': '',  'author': '', 'year': '', 'journal': '', 'file': '', 'booktitle': '', 'tags': ',', 'pages':  '', 'volume': '', 'created_time': '01/01/1994 00:00:00'}
    DATETIME_FORMAT = '%m/%d/%Y %H:%M:%S'
    def __init__(self):
        self.current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        # self.collection_tree = \
        #         {'community_detection':{'constrained_clustering': {'active':  {'test': {}}, 'proof': {}}, 'constrastive_learning':  {}, 'mm':  {}},
        #         'reading': {'diffusion': {'low':  {}}, 'gen': {}},
        #         'math':{},
        #          'volmin': {'pertubation': {}},
        #          'book': {}
        #          }
        with open('./data/collection_tree.txt', 'rt') as file_handler:
            self.collection_tree = json.load(file_handler)
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            bib_database = bibtexparser.load(bibfile)
        self.papers = DatabaseManager.preprocessing(bib_database.entries)

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
            papers[i]['tags'] = ','.join(papers[i]['tags'])
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
        default_item = DatabaseManager.DEFAULT_ITEM.copy()
        default_item.update(paper_info)
        default_item['ID'] = str(random.randint(0, 100000000000))
        default_item['ENTRYTYPE'] = 'inproceedings'
        now = datetime.now()
        default_item['created_time'] = now.strftime(DatabaseManager.DATETIME_FORMAT)
        self.papers.append(default_item)

        self.dump()
        self.reload()

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


if __name__ == "__main__":
    import others
    db = DatabaseManager()
    # db.update_paper('test', 'file', 'filefile')
    db.dump()
    # db.get_paper_attributes('test')
    # print(others.export_bib_format(db.bib_database.entries[0]))


import json
from tqdm import tqdm
import bibtexparser
import shutil
import os
import random

from bibtexparser.bibdatabase import BibDatabase


class DatabaseManager(object):
    """
    VERY BUGGY.
    Next step: eliminate dependence on this poor Bibtexparser
    """

    def __init__(self):
        self.current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        self.collection_tree = {'community_detection':{'related_works': {'active':  {'test': {}}}, },
                'reading': {'diffusion': {}}}
        with open('./data/bib_collection.bib', 'rt') as bibfile:
            bib_database = bibtexparser.load(bibfile)
        self.papers = DatabaseManager.preprocessing(bib_database.entries)

    def preprocessing(papers):
        result = []
        for paper in papers:
            new_paper = paper.copy()
            default_item = {'title': '',  'author': '', 'year': '', 'journal': '', 'file': '', 'booktitle': '', 'tags': ','}
            new_paper['tags'] = set([item.strip() for item in paper['tags'].split(',')])
            default_item.update(new_paper)
            result.append(default_item)
        return result
    def post_preprocess(papers):
        for i in range(len(papers)):
            papers[i]['tags'] = ','.join(papers[i]['tags'])
        return papers

    def get_collection(self):
        return self.collection_tree

    def get_list_papers(self, tags):
        result = []
        tags = set(tags)
        return [paper for paper in self.papers if tags.issubset(paper['tags'])]

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
        src = os.path.join(self.current_path, 'data', 'bib_collection.bib')
        dst = os.path.join(self.current_path, 'data', '.bib_collection.bib')
        shutil.copyfile(src, dst)

        bib_database = BibDatabase()
        bib_database.entries = DatabaseManager.post_preprocess(self.papers)
        with open(src, 'wt') as bibtex_file:
            bibtexparser.dump(bib_database, bibtex_file)

    def _look_paper_up(self, paper_id):
        for paper in self.papers:
            if paper['ID'] == paper_id:
                return paper

    def add_paper(self, paper_info):
        default_item = {'title': '',  'author': '', 'year': '', 'journal': '', 'file': '', 'booktitle': '', 'tags': ','}
        default_item.update(paper_info)
        default_item['ID'] = str(random.randint(0, 100000000000))
        default_item['ENTRYTYPE'] = 'inproceedings'
        self.papers.append(default_item)

        self.dump()
        self.reload()


if __name__ == "__main__":
    import others
    db = DatabaseManager()
    # db.update_paper('test', 'file', 'filefile')
    # db.dump()
    # db.get_paper_attributes('test')
    print(others.export_bib_format(db.bib_database.entries[0]))


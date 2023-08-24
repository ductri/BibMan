from datetime import datetime
from tqdm import tqdm

from bibman.utils.data_manager import DatabaseManager


def main():
    database = DatabaseManager()
    all_papers = database.get_list_papers(['default'])
    all_papers = sorted(all_papers, key=lambda p: datetime.strptime(p['created_time'], DatabaseManager.DATETIME_FORMAT), reverse=False)
    # for i, paper in tqdm(enumerate(all_papers), total=len(all_papers)):
    #     paper_id = paper['ID']
    #     paper['__order_value'] = str(i)

    print('dumping database')
    database.update_batch_paper(
            [paper['ID'] for paper in all_papers], \
            '__order_value', \
            [str(i) for i in range(len(all_papers))])


if __name__ == "__main__":
    main()

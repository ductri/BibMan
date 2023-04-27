import requests


def download_file(url, path_to_file, chunk_size=2000):
    try:
        r = requests.get(url, stream=True)

        with open(path_to_file, 'wb') as fd:
            for chunk in r.iter_content(chunk_size):
                fd.write(chunk)
        return True
    except:
        return False


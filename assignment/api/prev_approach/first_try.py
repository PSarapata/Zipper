"""This is what I tried at first, might help when trying to understand my thought process.
Output was a local copy of downloaded files, stored in a folder named as hash. Then, ZipFile was called on this
folder and user ended up with sort of a 'clone'. Inefficient, therefore I started digging and found a better way."""
import shutil
from os.path import basename
from zipfile import ZipFile
import re
import os

import requests

from assignment.settings import BASE_DIR


def download_list_and_zip_it(url_list, hash, chunk_size=512):
    def getFilename_fromCd(cd):
        """
        Get filename from content-disposition
        """
        if not cd:
            return None
        fname = re.findall('filename=(.+)', cd)
        if len(fname) == 0:
            return None
        return fname[0]

    def zip_it_buddy(path=None):
        # create a ZipFile instance
        if path is not None:
            try:
                with ZipFile((path + '.zip'), 'w') as zipObj:
                    # iterate over all files in the catalogue
                    for folderName, subfolders, filenames in os.walk(path):
                        for filename in filenames:
                            # create complete filepath of file in directory
                            file_path = os.path.join(folderName, filename)
                            # add file to zip
                            zipObj.write(file_path, basename(file_path))
                print("All good, your zipped archive is ready. Smashin'.")
                return True
            except Exception as exc:
                print(exc)
                raise exc
        else:
            print('Path is empty, something went wrong.')
            return False

    directory = 'api/media/{}'.format(hash)
    parent_dir = BASE_DIR
    path = os.path.join(parent_dir, directory)
    os.mkdir(path)
    print('Directory %s created' % directory)
    print('Downloading...')
    for url in url_list:
        r = requests.get(url, allow_redirects=True, stream=True)
        filename = getFilename_fromCd(r.headers.get('content-disposition'))
        if not filename:
            filename = url.split('/')[-1]
        with open((path + '/' + filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
    print('Download completed!')
    print("You should see your data here: {} !".format(path))
    zip_it_buddy(path)
    shutil.rmtree(path)
    return True

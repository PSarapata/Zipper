from django.http import HttpResponse, HttpResponseRedirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from assignment.settings import BASE_DIR
import os
import json
import requests
import uuid
import time
import re
from zipfile import ZipFile
from os.path import basename


class TestView(View):
    def get(self, request):
        return HttpResponse("ok.")


@method_decorator(csrf_exempt, name='dispatch')
class ReceiveURL(View):
    def get(self, request):
        return HttpResponse('hello.')

    def post(self, request):
        try:
            reqbody = json.loads(request.body.decode())

            # We got the list with urls, now let's download dem fuckerz.
            url_list = reqbody["urls"]

            if (type(url_list) == list) and url_list is not None:

                # Generate hash and send it with the response
                hash = str(uuid.uuid4())
                try:
                    download_list_and_zip_it(url_list, hash)
                    return HttpResponse("Success!")
                except Exception as err:
                    raise err

        except Exception as e:
            raise e


def download_list_and_zip_it(url_list, hash):
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

    directory = 'api/databank/{}'.format(hash)
    parent_dir = BASE_DIR
    path = os.path.join(parent_dir, directory)
    os.mkdir(path)
    print('Directory %s created' % directory)
    for url in url_list:
        r = requests.get(url, allow_redirects=True)
        filename = getFilename_fromCd(r.headers.get('content-disposition'))
        if not filename:
            filename = url.split('/')[-1]
        with open((path + '/' + filename), 'wb') as f:
            f.write(r.content)
    print("You should see your data here: {} !".format(path))
    zip_it_buddy(path)
    return True


class SendArchive(View):
    def get(self, request, hash=''):
        # check if hash has been processed
        # yes? -> send files
        # no? --> tell them to wait
        content = ''

        def myfunc(hash):
            self.content = {"status": "in-progress"}
            return self.content

        if myfunc(hash):
            return HttpResponseRedirect(f'{hash}/', content=content)

        return HttpResponse('ok, here is your file or not okay and gtfo.')

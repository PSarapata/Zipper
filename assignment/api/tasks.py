import io
import sys
import json
from zipfile import ZipFile

import requests
from celery import shared_task
from django.core.files.storage import FileSystemStorage

from api.models import AsyncResults


# app = Celery('tasks', broker='pyamqp://guest@localhost//')


# bind the task to itself to ensure that task results get associated with the correct task id
@shared_task(bind=True)  # for bound celery tasks, you need to pass in self as the first argument
def initiate_download(self, **kwargs):
    """
    Task: Generate a data report, store for download, and save the
    download URL to AsyncResults model once task finishes running
    """
    try:
        # create AsyncResult:
        url_list = kwargs.get('url_list', None)
        hash = kwargs.get('hash', None)
        initial_result = {"status": "in-progress"}
        initial_json_result = json.dumps(initial_result, indent=4)
        AsyncResults.objects.create(task_id=hash, result=initial_json_result)
        # function to generate, upload the archive to django filestorage, then return archive's url
        download_url = download(url_list=url_list, hash=hash)
        # get related result from the db and update the status.
        success_result = {"status": "completed",
                          "url": download_url}
        success_json_result = json.dumps(success_result, indent=4)
        async_result = AsyncResults.objects.get(task_id=hash)
        async_result.result = success_json_result
        async_result.save()
    except:
        # save error messages with status code 500
        result = {"status": 500,
                  "error_message": str(sys.exc_info()[0])}
        json_result = json.dumps(result)
        async_res = AsyncResults.objects.get_or_create(task_id=kwargs.get('hash'))[0]
        async_res.result = json_result
        async_res.save()


def download(url_list, hash):
    """
    Input: urls for download, hash = task_id,
    Output: single url with path on the server where archive is served.
    """
    try:
        # initiate in-memory-file-like-object(our archive)
        in_memory_archive = io.BytesIO()

        with ZipFile(in_memory_archive, 'a') as zf:
            # read contents of each media (any) files from the urls
            for url in url_list:
                r = requests.get(url, allow_redirects=True)
                filename = url.split('/')[-1]
                zf.writestr(filename, r.content)

        # fix for Linux zip files read in Windows
        for file in zf.filelist:
            file.create_system = 0
        zf.close()

        fs = FileSystemStorage()
        in_memory_archive.flush()
        fname = fs.save(hash + '.zip', in_memory_archive)
        url = "http://localhost:8000/%s" % fs.url(fname)
        return url

    except Exception as e:
        print(filename)
        print(e)
        raise e

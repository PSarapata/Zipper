import io
import sys
import json
import aiohttp
import asyncio
from zipfile import ZipFile
from kombu.exceptions import OperationalError

import requests
from celery import shared_task
from django.core.files.storage import FileSystemStorage

from api.models import AsyncResults
from datetime import datetime, timedelta

# app = Celery('tasks', broker='pyamqp://guest@localhost/')


# bind the task to itself to ensure that task results get associated with the correct task id
@shared_task(bind=True)  # for bound celery tasks, you need to pass in self as the first argument
def initiate_download(self, **kwargs):
    """
    Task: Generate a data report, store for download, and save the
    download URL to AsyncResults model once task finishes running
    """
    try:
        # update AsyncResult:
        url_list = kwargs.get('url_list', None)
        hash = kwargs.get('hash', None)
        # function to generate, upload the archive to django filestorage, then return archive's url
        download_url = download(url_list=url_list, hash=hash)
        # get related result from the db and update the status.
        success_result = {"status": "completed", "url": download_url}
        success_json_result = json.dumps(success_result, indent=4)
        async_result = AsyncResults.objects.get(task_id=hash)
        async_result.result = success_json_result
        async_result.save()
        # call a webhook but apply execution time limit of 1 hour.
        send_notification.delay(url=download_url, expires=datetime.now() + timedelta(hours=1), ignore_result=True)
    # in case our task fails due to connection error lasting longer than 3 retries
    except OperationalError:
        error_result = json.dumps({"status": "failed", "error_message": 'Potential Network Error' + repr(
            OperationalError)}, indent=4)
        # this and the below get_or_create will cover us in case the task was not created before the task started.
        async_result = AsyncResults.objects.get_or_create(task_id=kwargs.get('hash'))[0]
        async_result.result = error_result
        async_result.save()
    except:
        # save error messages with status code 500
        result = {"status": 500,
                  "error_message": str(sys.exc_info()[0])}
        json_result = json.dumps(result)
        async_res = AsyncResults.objects.get_or_create(task_id=kwargs.get('hash'))[0]
        async_res.result = json_result
        async_res.save()


@shared_task
def send_notification(**kwargs):
    """
    Calls a custom webhook service on IFTTT (if this then that) website which then sends a notification via
    smartphone APP to the customer that the download finished.
    """
    url = kwargs.get('url', None)
    if url is not None:
        iftt_url = 'https://maker.ifttt.com/trigger/download_ready/with/key/cX2k9A3tnmE4UGl0q2v_kW/'
        request = requests.post(iftt_url, {"value1": url})
        return request


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
                # handling missing files
                if r.status_code == 404:
                    pass
                filename = url.split('/')[-1]
                zf.writestr(filename, r.content)

        # fix for Linux zip files read in Windows
        for file in zf.filelist:
            file.create_system = 0
        zf.close()

        fs = FileSystemStorage()
        in_memory_archive.flush()
        fs.save(hash + '.zip', in_memory_archive)
        #  Warning: hardcoded, since I was receiving duplicate paths - probably after fiddling with DEBUG settings.
        url = 'http://localhost:8000/api/archive/get/%s.zip/' % hash
        return url

    except Exception as e:
        print(filename)
        print(e)
        raise e


async def async_download(url_list, hash):
    """
    Under development. In theory should shorten the execution time and handle missing
    files better.
    """

    async def download_single_file(url, session, zf):
        async with session.get(url) as response:
            resp = response.read()
            await resp
            filename = url.split('/')[-1]
            return await zf.writestr(filename, resp)

    async def multidownload(url_list, zf):
        async with aiohttp.ClientSession() as session:
            for url in url_list:
                ready_file = await download_single_file(url, session, zf)
                return ready_file

    try:
        in_memory_archive = io.BytesIO()

        with ZipFile(in_memory_archive, 'a') as zf:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(multidownload(url_list=url_list, zf=zf))

        # fix for Linux zip files read in Windows
        for file in zf.filelist:
            file.create_system = 0
        zf.close()

        fs = FileSystemStorage()
        in_memory_archive.flush()
        await fs.save(hash + '.zip', in_memory_archive)

        url = 'http://localhost:8000/api/archive/get/%s.zip/' % hash
        return await url

    except Exception as exc:
        print(exc)
        raise exc

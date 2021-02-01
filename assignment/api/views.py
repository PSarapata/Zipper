"""Please note: this is a naive approach - I found out 15% towards the end about the existance of boto3 library which
should handle all this stuff for us. Whoopsie.
This approach is based on the following article:

https://medium.com/@yootar/asynchronous-downloads-in-django-with-celery-5ff4433c62dc

Please note it wasn't easy to find out how to integrate all this - and make it cooperate, there are no easy
answers on the web and to finally reach something I could use (and understand) took over 48 hours. The entire concept
of in-memory-data flow is also quite new to me, but definitely what I struggled with the most was the use of Celery /
ansynchronizing the request-response communication between endpoints.
"""

from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from api.tasks import initiate_download
from api.models import AsyncResults

from django.core.files.storage import FileSystemStorage

import json
import requests
import uuid
import io

from zipfile import ZipFile


@method_decorator(csrf_exempt, name='dispatch')
class ReceiveHash(View):
    """
    Initiates asynchronous task to download and serve archive to the client.
    Returns task id with the response.
    """

    def post(self, request):
        try:
            reqbody = json.loads(request.body.decode())

            url_list = reqbody["urls"]

            if (type(url_list) == list) and url_list is not None:

                # Generate hash and send it with the response
                hash = str(uuid.uuid4())
                try:
                    # start the download task
                    print("Initiating Celery task...")
                    task = initiate_download.delay(url_list=url_list, hash=hash)
                    print("Task %s initiated..." % task.task_id)
                    # send status with the response
                    resp = {"active_hash": "%s" % hash}
                    response = HttpResponse(json.dumps(resp, indent=4), status=202)
                    return response

                    # store task refs
                    # request.session['url_list'] = url_list
                    # request.session['status'] = 'in-progress'
                    # request.session['hash'] = hash
                    # # can't get session to work in cache, therefore 24hrs cookies as a backup...
                    # resp = {"archive_hash": "%s" % request.session['hash']}
                    # response = HttpResponse(json.dumps(resp, indent=4))
                    # response.set_cookie('hash', hash, max_age=86400)
                    # response.set_cookie('url_list', url_list, max_age=86400)
                    # response.set_cookie('status', 'in-progress', max_age=86400)
                    # return response

                except Exception as err:
                    raise err

        except Exception as e:
            raise e


def download(url_list, hash):
    """
    Input: urls for download, hash = task_id,
    Output: single url with path on the server where archive is served.
    """
    # regex to validate if hash is valid (obsolete with this approach):
    # ('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$/i', hash):
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
        # attach our zipped catalogue to response
        # response = HttpResponse()
        # response["Content-Type"] = 'application/zip'
        # response["Content-Disposition"] = f"attachment; filename={hash + '.zip'}"  ------> file as attachment version

        fs = FileSystemStorage()
        in_memory_archive.flush()
        fname = fs.save(hash + '.zip', in_memory_archive)
        url = "http://localhost:8000/%s" % fs.url(fname)
        return url
        # in_memory_archive.seek(0)
        # response.write(in_memory_archive.read())                    --------------> attach file to response version
        # return response

    except Exception as e:
        print(filename)
        print(e)
        raise e
    # return HttpResponse("The hash you provided is invalid.") --------> in case we wanted to validate hash


class CheckStatus(View):
    """
    API endpoint that returns whether an Async job is finished, and
    what to do with the job.  Once a related Async task finishes, it saves a JSON blob to
    AsyncResults table. PollAsyncResultsView looks for a JSON blob
    associated with the given task id and returns 202 Accepted
    until it finds one.
    The JSON blob looks like the below
    { status: completed,
      url: download url,
    }
    or if there was an error processing the task,
    { status_code: 500, error_message: error message}
    """

    def get(self, request, hash):
        task_id = self.kwargs.get('hash', None)
        # we are expecting only one task for the given hash-user pair
        async_result = AsyncResults.objects.get(task_id=task_id)
        if async_result:
            load_body = json.loads(async_result.result)
            status = load_body.get('status', None)

            # in case something went wrong we'll get 500 internal server error with a message:
            if status == 500:
                return HttpResponse(json.dumps(load_body.get('error_message', None), indent=4), status=500)
            # on success:
            else:
                return HttpResponse(json.dumps(load_body, indent=4), status=200)
        # task is still being processed:
        else:
            resp = {"status": "in-progress"}
            return HttpResponse(json.dumps(resp, indent=4))
        # return HttpResponse('Hash invalid.')


class TestView(View):
    def get(self, request):
        request.session['url'] = 'https://medium.com/better-programming/managing-sessions-in-django-92ef72db4c63'
        request.session['url_list'] = ['some_url', 'some_other_url', 'testing_my_urls']
        request.session['test'] = 'just a test'
        response = HttpResponse("hopefully I set my session.")
        response.set_cookie('url', 'https://medium.com/better-programming/managing-sessions-in-django-92ef72db4c63',
                            max_age=86400)
        response.set_cookie('url_list', ['some_url', 'some_other_url', 'testing_my_urls'], max_age=86400)
        return response

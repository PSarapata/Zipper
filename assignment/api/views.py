"""Please note: this is a naive approach - I found out 15% towards the end about the existance of boto3 library which
should handle all this stuff for us. Whoopsie.
This approach is based on the following article:

https://medium.com/@yootar/asynchronous-downloads-in-django-with-celery-5ff4433c62dc

Please note it wasn't easy to find out how to integrate all this - and make it cooperate, there are no easy
answers on the web and to finally reach something I could use (and understand) took over 48 hours. The entire concept
of in-memory-data flow is also quite new to me, but definitely what I struggled with the most was the use of Celery /
ansynchronizing the request-response communication between endpoints.
"""
import re

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from api.tasks import initiate_download
from api.models import AsyncResults
from datetime import datetime, timedelta

import json
import uuid


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
                    # start the download task, limit execution time to 12 hours, default is 3 retries...
                    print("Initiating Celery task...")
                    task = initiate_download.delay(url_list=url_list, hash=hash, expires=datetime.now() + timedelta(
                        hours=12))
                    print("Task %s initiated..." % task.task_id)
                    # send status with the response
                    resp = {"active_hash": "%s" % hash}
                    response = HttpResponse(json.dumps(resp, indent=4), status=202)
                    return response

                except Exception as err:
                    raise err

        except Exception as e:
            raise e


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
        if validate_uuid(hash):
            try:
                async_result = AsyncResults.objects.get(task_id=task_id)
                if async_result:
                    load_body = json.loads(async_result.result)
                    status = load_body.get('status', None)

                    # in case something went wrong we'll get 500 internal server error with a message or network
                    # failure:
                    if status == 500 or status == 'failed':
                        return HttpResponse(json.dumps(load_body.get('error_message', None), indent=4), status=410)
                    # on success:
                    else:
                        return HttpResponse(json.dumps(load_body, indent=4), status=200)
                # task is still being processed:
                else:
                    resp = {"status": "in-progress"}
                    return HttpResponse(json.dumps(resp, indent=4), status=202)
            # I'm not proud about this one. What happens is we only get the actual AsyncResult once the worker comes
            # back to us. I have a possible solution in place but first I'd like to test it.
            except ObjectDoesNotExist:
                resp = {"status": "in-progress"}
                return HttpResponse(json.dumps(resp, indent=4), status=202)
            except Exception as error:
                print(error)
                raise error
        else:
            return HttpResponse("Invalid hash.")


def validate_uuid(hash):
    """Check if the user supplied valid hash to the view. That should save him the wait... :D"""
    regex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$'
    if re.search(re.compile(regex), hash):
        return True
    else:
        return False

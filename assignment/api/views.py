"""Please note: this is a naive approach - I found out 15% towards the end about the existance of boto3 library which
should handle all this stuff for us. Whoopsie."""


from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage

import json
import requests
import uuid
import io

from zipfile import ZipFile


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
                    request.session['status'] = 'in-progress'
                    request.session['hash'] = hash
                    resp = {"archive_hash": "%s" % request.session['hash']}
                    return HttpResponse(json.dumps(resp, indent=4))

                except Exception as err:
                    raise err

        except Exception as e:
            raise e


@csrf_exempt
def download(request, hash):
    body = json.loads(request.body.decode())
    url_list = body['urls']
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
        response = HttpResponse()
        response["Content-Type"] = 'application/zip'
        response["Content-Disposition"] = f"attachment; filename={hash + '.zip'}"

        in_memory_archive.seek(0)
        response.write(in_memory_archive.read())

        return response

    except Exception as e:
        print(filename)
        print(e)
        raise e


@csrf_exempt
def upload(request):
    context = {}
    if request.method == "POST":
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        context["url"] = fs.url(filename)

        # carry data along to Check Status View
        request.session["url"] = fs.url(filename)
        request.session["status"] = 'completed'
        return redirect('check_status')
    return render(request, 'upload.html', context)


class CheckStatus(View):
    def get(self, request):
        if 'status' in request.session.keys():
            if request.session['status'] == 'in-progress':
                resp = {"status": "%s" % request.session['status']}
                return HttpResponse(json.dumps(resp, indent=4))
            if request.session['status'] == 'completed' and 'hash' in request.session.keys():
                return redirect('send_archive', hash=request.session['hash'])
        return HttpResponse("No files queued.")


class SendArchive(View):
    def get(self, request, hash):
        """If the job is finished, display data and clear session. If not, display status. Else -> Notify that hash
        has expired or something went wrong."""
        if 'status' in request.session.keys():
            if request.session['status'] == 'completed':
                url = request.session['url']
                print(url)
                for key in list(request.session.keys()):
                    if not (key.startswith("_") and key == 'url'):  # Safer than session.flush(), won't log off the
                        # user.
                        del request.session[key]
                resp = {"status": "completed", "url": "%s" % url}
                print(resp)
                del request.session['url']
                return HttpResponse(json.dumps(resp, indent=4))
            if request.session['status'] == 'in-progress':
                resp = {"status": "%s" % request.session['status']}
                return HttpResponse(json.dumps(resp, indent=4))
        return HttpResponse('Hash invalid.')

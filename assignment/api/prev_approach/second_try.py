"""
This used to be one of the Views before I found out about async solution.
"""


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


"""Those were my ideas to transfer data synchronously between views..."""
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

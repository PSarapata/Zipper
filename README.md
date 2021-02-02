# Zipper
Coding Assignment


**Instructions:**

* create a virtual environment, at best at the same level as assignment (upper)
* pip install -r requirements.txt
* start rabbitmq server: `systemctl start rabbitmq-server`
* check if rabbitmq server is working: `systemctl status rabbitmq-server`
* if it works, activate celery worker (from terminal, in assignment directory(upper)): `celery -A tasks worker --loglevel=INFO`
* in another terminal window, start django server -> `python manage.py runserver`
* API runs as expected in DEBUG mode. Outside, I still haven't figure out which address points to Uploaded files / 
  how to activate FileSystemStorage outside of DEBUG mode. (Django should not be used for that in production anyway).

**If you follow these steps it should be good to go, celery will start the task and give you the hash. 
Download is currently synchronous and takes on average 30 seconds for a 14 MB archive. If we made it asynchronous 
that would be considerably shorter, but like I said - I don't want to mess things up playing with it too much.**


### EXTRAS ###

---------------
- [ ] Error handling is top-notch: invalid HTTP responses, handling missing files
      etc. - **partially** secured, result will return error message data in case something goes wrong server side 
      (result is tied to the same hash).
  
- [x] **Predefined webhook (another server) being called when archive generation
      job is finished.** - I used a low-code solution IFTT to get a notification on my smartphone whenever the 
      download is finished. (see tasks.py)
  
- [x] **The archive generation succeeds even in case of network errors and is
      capable of resuming the downloads.** - Checked with a very short network disconnection, the celery worker 
      resumed right after the network switched back on.

- [x] **The archive generation succeeds even if the API server is being restarted
      during the job run.** - checked, works. Once celery worker intercepts the task, 
      it is then handled independently.


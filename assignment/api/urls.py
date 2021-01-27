from django.urls import path
from api.views import TestView, ReceiveURL, SendArchive

urlpatterns = [
    path('', TestView.as_view(), name='testing'),
    path('create/', ReceiveURL.as_view(), name='receive_url'),
    path('status/', SendArchive.as_view(), name='send_hash'),
    path('status/<slug:hash>/', SendArchive.as_view(), name='send_archive'),
]

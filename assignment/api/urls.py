from django.urls import path
from api.views import TestView, ReceiveURL, SendArchive, upload, download, CheckStatus


urlpatterns = [
    path('', TestView.as_view(), name='testing'),
    path('create/', ReceiveURL.as_view(), name='receive_url'),
    path('status/', CheckStatus.as_view(), name='check_status'),
    path('upload/', upload, name='upload'),
    path('download/<slug:hash>/', download, name='download'),
    path('status/<slug:hash>/', SendArchive.as_view(), name='send_archive'),
]

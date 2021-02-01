from django.urls import path
from api.views import ReceiveHash, CheckStatus, download, TestView


urlpatterns = [
    path('test/', TestView.as_view(), name='test'),
    path('create/', ReceiveHash.as_view(), name='receive_url'),
    # path('status/', CheckStatus.as_view(), name='check_status'), ------> obsolete
    # path('upload/', upload, name='upload'), -----> obsolete
    path('download/<slug:hash>/', download, name='download'),
    path('status/<slug:hash>/', CheckStatus.as_view(), name='send_archive'),
]

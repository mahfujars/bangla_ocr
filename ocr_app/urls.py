from django.urls import path
from . import views

urlpatterns = [
    path('bangla_ocr/', views.upload_file, name='upload_file'),
    path('bangla_ocr/result/<str:unique_name>/', views.result, name='result'),
    path('bangla_ocr/download/<str:project_id>/<str:unique_name>/', views.download_ocr_file, name='download_ocr_file'),
]

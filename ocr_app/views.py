import os
import requests
from requests.exceptions import RequestException, ConnectionError
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import Http404
from django.http import StreamingHttpResponse

def upload_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            messages.error(request, "No file selected. Please choose a file to upload.")
            return render(request, 'upload.html')

        url = 'https://ocr.bangla.gov.bd/files/upload_v3/0/uploadandocr'
        data = {
            'userId': '0',
            'targetedStatus': 'DOCX_GENERATED',
            'documentType': 'cc',
            'isNewspaper': 'false',
            'ocrModelType': 'hybridModel',
            'keepEnglish': 'false'
        }
        headers = {
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://ocr.bangla.gov.bd',
            'user-agent': request.META.get('HTTP_USER_AGENT', 'Mozilla/5.0'),
        }

        try:
            files = {
                'file': (uploaded_file.name, uploaded_file, uploaded_file.content_type)
            }
            response = requests.post(url, headers=headers, data=data, files=files, timeout=10)

            if response.status_code == 412:
                error_msg = response.json().get("message", "Precondition Failed.")
                messages.error(request, f'OCR Error: {error_msg}')
            else:
                response.raise_for_status()
                data = response.json()
                unique_name = data.get("uniqueName")
                if unique_name:
                    return redirect('result', unique_name=unique_name)
                else:
                    messages.error(request, 'Failed to get unique name from OCR service.')

        except ConnectionError:
            messages.error(request, "No internet connection. Please check your network.")
        except RequestException as e:
            messages.error(request, f'Error uploading file: {str(e)}')

    return render(request, 'upload.html')


def result(request, unique_name):
    status_url = f'https://ocr.bangla.gov.bd/project/uuid_status/{unique_name}'
    headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://ocr.bangla.gov.bd',
        'user-agent': request.META.get('HTTP_USER_AGENT', 'Mozilla/5.0'),
    }

    status = None
    download_url = None

    try:
        response = requests.get(status_url, headers=headers, timeout=10)
        response.raise_for_status()
        status_data = response.json()
        status = status_data.get("currentStatus")
        project_id = status_data.get("projectId")

        if status == "DOCX_GENERATED":
            # Store file locally and serve from your own domain (if needed)
            download_url = f"/bangla_ocr/download/{project_id}/{unique_name}/"

    except ConnectionError:
        messages.error(request, "No internet connection. Please check your network.")
    except RequestException as e:
        messages.error(request, f"Error checking status: {str(e)}")

    return render(request, 'result.html', {
        'unique_name': unique_name,
        'status': status,
        'download_url': download_url,
    })


def download_ocr_file(request, project_id, unique_name):
    status_url = f'https://ocr.bangla.gov.bd/project/uuid_status/{unique_name}'
    headers = {
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://ocr.bangla.gov.bd',
        'user-agent': request.META.get('HTTP_USER_AGENT', 'Mozilla/5.0'),
    }

    try:
        status_response = requests.get(status_url, headers=headers)
        status_response.raise_for_status()
        status_data = status_response.json()
        project_id = status_data.get("projectId")

        if not project_id:
            raise Http404("Project ID not found.")

        file_url = f'https://ocr.bangla.gov.bd/files/file_v3/ocroutputfile/{project_id}?fileName={unique_name}&level=PROJECT&fileType=docx'
        file_response = requests.get(file_url, headers=headers, stream=True)
        file_response.raise_for_status()

        response = StreamingHttpResponse(
            file_response.raw,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="{unique_name}.docx"'
        return response

    except requests.RequestException:
        raise Http404("Error downloading OCR file.")

import io
import os
import json
import logging

import requests
from flask import make_response
from PyPDF2 import PdfFileMerger

# no log file config, log can be read by docker logs or kubectl logs
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s",
    level=logging.INFO)

DTABLE_WEB_SERVICE_URL = os.environ.get('DTABLE_WEB_SERVICE_URL')
if not DTABLE_WEB_SERVICE_URL:
    logging.critical('DTABLE_WEB_SERVICE_URL invalid!')
    exit(1)

DOWNLOAD_URL = 'api/v2.1/dtable/app-download-link/'


def handle(request, context):
    """
    must return a Response instance or return 500 with nothing
    """
    if request.method != 'POST':
        return make_response(('Method %s not allowed.' % (request.method,), 403))

    # Authorization token
    api_token = request.headers.get('Authorization', '').split()
    if not api_token or api_token[0].lower() != 'token' or len(api_token) != 2:
        return make_response(('Permission denied.', 403))
    api_token = api_token[1]

    # get json data
    try:
        data = json.loads(request.get_data(as_text=True))
    except:
        return make_response(('Parameters invalid.', 400))

    # arguments check
    files = data.get('files')
    if not files or isinstance('files', list):
        return make_response(('files invalid.', 400))
    for file in files:
        if not file.strip('/').endswith('.pdf'):
            return make_response(('file %s invalid.' % (file,), 400))
    username = data.get('username')
    dtable_uuid = data.get('dtable_uuid')

    # prepare to get download url
    urls = []
    get_download_url = DTABLE_WEB_SERVICE_URL.strip('/') + '/' + DOWNLOAD_URL.lstrip('/')
    headers = {
        'Authorization': 'Token ' + api_token
    }

    # temp api-token need username and dtable_uuid when get download link
    if username and dtable_uuid:
        params = {
            'username': username,
            'dtable_uuid': dtable_uuid
        }
    else:
        params = {}

    for file in files:
        params['path'] = file
        try:
            response = requests.get(get_download_url, params=params, headers=headers)
            if response.status_code != 200:
                if response.status_code == 403:
                    return make_response(('Permission denied.', 403))
                logging.error('get file: %s download-link status code: %s, resp: %s',
                            file, response.status_code, response.content)
                return make_response(('Internal Server Error.', 500))
            data = response.json()
            download_link = data.get('download_link')
            if not download_link:
                logging.error('get file: %s, download_link not in data: %s', file, response.content)
                return make_response(('Internal Server Error.', 500))
            urls.append(download_link)
        except Exception as e:
            logging.error('get file: %s download-link error: %s', file, e)
            return make_response(('Internal Server Error.', 500))

    # merge and return
    merger = PdfFileMerger()
    for url in urls:
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                logging.warning('request url: %s status code: %s', url, resp.status_code)
                return make_response(('URL: %s invalid.' % (url,), 400))
        except Exception as e:
            logging.error('request url: %s error: %s', url, e)
            return make_response(('URL: %s invalid.' % (url,), 400))
        try:
            merger.append(io.BufferedReader(io.BytesIO(resp.content)))
        except Exception as e:
            logging.error('url: %s fetch success but merge error: %s', url, e)
            return make_response(('Internal Server Error.', 500))

    merged_bytes = io.BytesIO()
    try:
        merger.write(merged_bytes)
    except Exception as e:
        logging.error('merge pdfs error: %s', e)
        return make_response(('Internal Server Error.', 500))

    response = make_response(merged_bytes.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment;filename*=' + 'merged.pdf'
    return response

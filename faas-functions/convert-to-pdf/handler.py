import io
import os
import json
import uuid
import logging
import subprocess

from flask import make_response, send_from_directory

# no log file config, log can be read by docker logs or kubectl logs
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s",
    level=logging.INFO)


def remove_file(file_path):
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except:
        pass


def handle(request, context):
    """
    must return a Response instance or return 500 with nothing
    """
    # arguments check
    try:
        original_file = request.files.get('file')
    except Exception as e:
        logging.error(e)
    if not original_file:
        return make_response(('file invalid.', 400))

    # file check
    file_name = original_file.filename
    if os.path.splitext(file_name)[-1] not in ['.docx']:
        return make_response(('file invalid.', 400))

    # save file
    file_no = uuid.uuid4().hex
    save_filename = file_no + os.path.splitext(file_name)[-1]
    pdf_filename = file_no + '.pdf'
    original_file.save(save_filename)

    # convert to pdf
    try:
        subprocess.run(['unoconv', '-f', 'pdf', save_filename])
    except Exception as e:
        logging.error(e)
        remove_file(save_filename)
        return make_response(('file invalid.', 400))

    if not os.path.isfile(pdf_filename):
        logging.error('no pdf file generated!')
        return make_response(('Internal Server Error'), 500)

    # return
    try:
        return send_from_directory(os.getcwd(), pdf_filename, as_attachment=True)
    except Exception as e:
        logging.error(e)
        return make_response(('Internal Server Error'), 500)
    finally:
        remove_file(save_filename)
        remove_file(pdf_filename)

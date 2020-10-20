import io
import json
import logging

import docxtpl
from flask import make_response

# no log file config, log can be read by docker logs or kubectl logs
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s",
    level=logging.INFO)


def handle(request, context):
    """
    must return a Response instance or return 500 with nothing
    """
    # arguments check
    try:
        docx_file = request.files.get('docx')
    except Exception as e:
        logging.error(e)
    if not docx_file:
        return make_response(('file invalid.', 400))

    try:
        context = json.loads(request.form.get('context'))
    except Exception as e:
        logging.error(e)
        return make_response(('context invalid.', 400))

    # read document
    try:
        doc = docxtpl.DocxTemplate(docx_file)
    except Exception as e:
        return make_response(("file is not a docx file.", 400))

    # render
    try:
        doc.render(context)
        rendered_docx_file = io.BytesIO()
        doc.save(rendered_docx_file)
    except Exception as e:
        logging.error(e)
        return make_response(('Internal Server Error.', 500))

    response = make_response(rendered_docx_file.getvalue())
    response.headers['Content-Type'] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    response.headers['Content-Disposition'] = 'attachment;filename*=' + 'result.docx'
    return response

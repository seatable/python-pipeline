import logging
from flask import make_response

# no log file config, log can be read by docker logs or kubectl logs
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s",
    level=logging.INFO)


def handle(request, context):
    """
    must return a Response instance or return 500 with nothing
    """
    return make_response(('success', 200))

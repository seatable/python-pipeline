#!/usr/bin/env python
from flask import Flask, request, jsonify, Response
from waitress import serve
import os

from function import handler

app = Flask(__name__)

class Context:
    def __init__(self):
        self.hostname = os.getenv('HOSTNAME', 'localhost')

@app.route('/', defaults={'path': ''}, methods=['GET', 'PUT', 'POST', 'PATCH', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'PUT', 'POST', 'PATCH', 'DELETE'])
def call_handler(path):
    context = Context()

    try:
        resp = handler.handle(request, context)
        if not isinstance(resp, Response):
            return ('', 500, [])
    except:
        return ('', 500, [])
    return resp

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000)

#!/usr/bin/env python

"""
simple.py - A really simple Trapeze-WSGI demo app.

Getting Started
---------------

1. Follow the instructions at http://github.com/paulj/trapeze until
(and including) "make run".
2. Run:
export PYTHONPATH=".:$PYTHONPATH"
python src/TrapezeWSGI.py "*.localhost.*./.#" demo.simple.WSGIHandler
from the top-level directory of trapeze-wsgi.
3. Visit http://localhost:55672/ in your web browser.

You should see "Hello World" in your browser.
"""


class WSGIHandler:
    def __call__(self, environ, start_response):
        start_response("200 OK", [])
        return ["<html><body>Hello World</body></html>"]

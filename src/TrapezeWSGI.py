#

#
# Copyright (c) 2010 John Weaver
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from amqplib import client_0_8 as amqp

from wsgiref.handlers import SimpleHandler
import mimetools
import os, os.path
import cStringIO
import inspect

#from pyamqpclient.configurableclient \
#import ClientWithNetAndFileConfig as Client

from pyamqpclient.configurableclient import ClientWithFileConfig as Client
from pyamqpclient.channel import Channel
from pyamqpclient.consumer import ReplyingConsumer

CONFIG_DIR = '/etc'


class TrapezeWSGIHandler(SimpleHandler):
    wsgi_run_once = False

    def __init__(self, stdin, stdout, stderr):
        base_environ = dict(os.environ.items())
        base_environ['SERVER_PROTOCOL'] = 'HTTP/1.0'
        SimpleHandler.__init__(self, stdin, stdout, stderr, base_environ,
                               multithread=False, multiprocess=True)

    def update_environ(self, environ):
        self.base_env.update(environ)


class TrapezeWSGI(Client):
    """
    Handle HTTP requests that have been encapsulated in an AMQP message
    by passing them via WSGI to a Python application.
    """
    queue = Channel(ReplyingConsumer, '_deliver_callback', 'trapeze',
                    {'durable': False, 'exclusive': False, 
                     'auto_delete': False})

    def __init__(self, application, routing_key, 
                 wsgi_handler=TrapezeWSGIHandler):
        """Initialize the AMQP connection, channel, and receiving queue."""
        self.output_buffer = cStringIO.StringIO()
        self.input_buffer = cStringIO.StringIO()
        self.error_buffer = cStringIO.StringIO()

        self.application = application
        self.handler = TrapezeWSGIHandler(self.input_buffer,
                                          self.output_buffer,
                                          self.error_buffer)
        Client.__init__(self, os.path.join(CONFIG_DIR, 'trapeze-wsgi.conf'))
        self.queue.set_routing_key(routing_key)

    def _extract_env(self, request_headers):
        """Extract necessary information from the HTTP request headers
        and store it in the WSGI environment dictionary.
        """

        stream = cStringIO.StringIO(request_headers)
        # this isn't a reliable method of doing this,
        # but since we only plan on supporting one client...
        [command, full_path, version] = stream.readline() \
                                        .split("\n", 1)[0].split()
        path_components = full_path.split('?', 1)
        path = path_components[0]
        if len(path_components) == 2:
            query = path_components[1]
        else:
            query = ''

        headers = mimetools.Message(stream)

        forwarded_host = headers.get('x-forwarded-host', '')
        if forwarded_host != '':
            host_parts = forwarded_host.split(':')
        else:
            host_parts = headers.get('host', '').split(':')

        # TODO this doesn't take HTTPS into account.
        # How could we tell if this request came to us via HTTPS
        # at this point?
        if len(host_parts) == 2:
            [host, port] = host_parts
        else:
            host = host_parts[0]
            port = 80

        env = {}
        env['REQUEST_METHOD'] = command
        env['SERVER_NAME'] = host
        env['SERVER_PORT'] = port
        env['REMOTE_HOST'] = None
        env['CONTENT_LENGTH'] = headers.get('Content-Length', 0)
        env['SCRIPT_NAME'] = ''
        env['PATH_INFO'] = path
        env['QUERY_STRING'] = query

        if headers.typeheader is None:
            env['CONTENT_TYPE'] = headers.type
        else:
            env['CONTENT_TYPE'] = headers.typeheader
            length = headers.getheader('content-length')
            if length:
                env['CONTENT_LENGTH'] = length

        env['HTTP_COOKIE'] = headers.getheader('cookie', '')

        return env

    def _deliver_callback(self, message):
        [headers, body] = message.body.split('\r\n\r\n')
        self.input_buffer.write(body)
        self.input_buffer.seek(0)

        # use self.handler.update_environ() to set environ vars
        env = self._extract_env(headers)
        self.handler.update_environ(env)

        self.handler.run(self.application)

        response = amqp.Message(self.output_buffer.getvalue(),
                                correlation_id=message.message_id)

        self.input_buffer.truncate(0)
        self.output_buffer.truncate(0)
        # TODO logging the contents of error buffer?
        self.error_buffer.truncate(0)

        return response

    def __del__(self):
        self.input_buffer.close()
        self.output_buffer.close()
        self.error_buffer.close()


def main():
    import sys
    (prog, args) = (sys.argv[0], sys.argv[1:])
    usage = """Usage: %s <ROUTING_KEY> <APPLICATION_MODULE_PATH>
The routing key to bind our queue to the exchange (e.g. "*.localhost.*./.#").
Module path to WSGI application (e.g. django.core.handlers.wsgi.WSGIHandler).
""" % (prog,)

    if len(args) != 2:
        print usage
        sys.exit(1)

    routing_key = args[0]
    application_mod_path = args[1]

    (application_mod_name, application_class_name) = \
        tuple(application_mod_path.rsplit('.', 1))

    application_module = __import__(application_mod_name,
                                    globals(), locals(),
                                    [application_class_name])
    application_object = getattr(application_module, application_class_name)

    if inspect.isclass(application_object):
        application = application_object()
    else:
        application = application_object

    trapezewsgi_server = TrapezeWSGI(application, routing_key)
    trapezewsgi_server.serve_forever()

if __name__ == '__main__':
    main()

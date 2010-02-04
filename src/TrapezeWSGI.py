from amqplib import client_0_8 as amqp

from wsgiref.handlers import SimpleHandler
import mimetools
import os
import cStringIO


class TrapezeWSGIHandler(SimpleHandler):
  wsgi_run_once = False

  def __init__(self, stdin, stdout, stderr):
    base_environ = dict(os.environ.items())
    base_environ['SERVER_PROTOCOL'] = 'HTTP/1.0'
    SimpleHandler.__init__(
      self, stdin, stdout, stderr, base_environ,
      multithread=False, multiprocess=True
    )

  def update_environ(self, environ):
    self.base_env.update(environ)
  

class TrapezeWSGI:
  DEFAULT_QUEUE_NAME = 'app'
  CONSUMER_TAG = 'consumer'

  def __init__(self, application, routing_key,
               connection_settings=('localhost:5672', 'guest', 'guest',
                                    '/', False),
               exchange='trapeze', wsgi_handler=SimpleHandler):
    self.output_buffer = cStringIO.StringIO()
    self.input_buffer = cStringIO.StringIO()
    self.error_buffer = cStringIO.StringIO()

    self.amqp_connection = amqp.Connection(host=connection_settings[0],
                                           userid=connection_settings[1],
                                           password=connection_settings[2],
                                           virtual_host=connection_settings[3],
                                           insist=connection_settings[4])
    self.amqp_channel = self.amqp_connection.channel()
    self.amqp_channel.queue_declare(queue=TrapezeWSGI.DEFAULT_QUEUE_NAME,
                                    durable=False, exclusive=False,
                                    auto_delete=False)
    self.amqp_channel.queue_bind(queue=TrapezeWSGI.DEFAULT_QUEUE_NAME,
                                 exchange=exchange, routing_key=routing_key)

    self.application = application
    self.handler = TrapezeWSGIHandler(self.input_buffer,
                                      self.output_buffer,
                                      self.error_buffer)

    self.amqp_channel.basic_consume(queue=TrapezeWSGI.DEFAULT_QUEUE_NAME,
                                    callback=self._deliver_callback,
                                    consumer_tag=TrapezeWSGI.CONSUMER_TAG,
                                    no_ack=True)

  def serve_forever(self):
    try:
      while True:
        self.handle_request(False)
    finally:
      self._cleanup()

  def _extract_env(self, request_headers):
    stream = cStringIO.StringIO(request_headers)
    # this isn't a reliable method of doing this, but since we only plan on supporting one client...
    [command, full_path, version] = stream.readline().split("\n", 1)[0].split()
    path_components = full_path.split('?', 1)
    path = path_components[0]
    if len(path_components) == 2:
      query = path_components[1]
    else:
      query = ''

    headers = mimetools.Message(stream)

    host_parts = headers.get('host', '').split(':')
    # TODO this doesn't take HTTPS into account. How could we tell if this request came to us via HTTPS at this point?
    if len(host_parts) == 2:
      [host, port] = host_parts
    else:
      host = host_parts[0]
      port = 80

    env = {}
    env['REQUEST_METHOD'] = command
    env['SERVER_NAME'] = host
    env['SERVER_PORT'] = port
    env['REMOTE_HOST'] = '127.0.0.1' # TODO ?
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
    print env
    self.handler.update_environ(env)
    
    self.handler.run(self.application)

    response = amqp.Message(self.output_buffer.getvalue(),
                            correlation_id=message.message_id)

    # don't ack until after wsgi app returns response and we are just about
    # to send that back to the queue.
    self.amqp_channel.basic_ack(message.delivery_tag)
    self.amqp_channel.basic_publish(response, routing_key=message.reply_to)
    self.input_buffer.truncate(0)
    self.output_buffer.truncate(0)
    # TODO logging the contents of error buffer?
    print self.error_buffer.getvalue()
    self.error_buffer.truncate(0)

  def handle_request(self, cleanup=True):
    try:
      self.amqp_channel.wait()
    finally:
      if cleanup:
        self._cleanup()

  def _cleanup(self):
    self.amqp_channel.basic_cancel(TrapezeWSGI.CONSUMER_TAG)
    self.input_buffer.close()
    self.output_buffer.close()
    self.error_buffer.close()
    self.amqp_channel.close()
    self.amqp_connection.close()


def main():
  import sys
  (prog, args) = (sys.argv[0], sys.argv[1:])
  usage = """Usage: %s <ROUTING_KEY> <APPLICATION_MODULE_PATH>
  The routing key to bind our queue to the exchange with (e.g. "*.localhost.*./.#").
  Python module path to WSGI application (e.g. django.core.handlers.wsgi.WSGIHandler)

          """ % (prog,)
  
  if len(args) != 2:
    print usage
    sys.exit(1)

  routing_key = args[0]
  application_mod_path = args[1]

  (application_mod_name, application_class_name) = tuple(application_mod_path.rsplit('.', 1))
  
  application_module = __import__(application_mod_name, globals(), locals(), [application_class_name])
  application = getattr(application_module, application_class_name)()
  trapezewsgi_server = TrapezeWSGI(application, routing_key)
  trapezewsgi_server.serve_forever()

if __name__ == '__main__':
  main()


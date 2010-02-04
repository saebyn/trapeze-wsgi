from amqplib import client_0_8 as amqp

from wsgiref.handlers import SimpleHandler
import os
import cStringIO


class TrapezeWSGIHandler(SimpleHandler):
  wsgi_run_once = True

  def __init__(self, stdin, stdout, stderr):
    BaseCGIHandler.__init__(
      self, stdin, stdout, stderr, dict(os.environ.items()),
      multithread=False, multiprocess=True
    )
  

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
    self.handler = TrapezeWSGIHandler(self.request_buffer,
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

  def deliver_callback(self, message):
    self.input_buffer.write(message.body)
    self.input_buffer.seek(0)
    
    self.handler.run(self.application)

    response = amqp.Message(self.output_buffer.getvalue(),
                            correlation_id=message.message_id)

    # don't ack until after wsgi app returns response and we are just about
    # to send that back to the queue.
    chan.basic_ack(message.delivery_tag)
    chan.basic_publish(response, routing_key=message.reply_to)
    self.input_buffer.truncate(0)
    self.output_buffer.truncate(0)
    # TODO logging the contents of error buffer?
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


def main(prog, args):
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

  (application_mod, application_class_name) = tuple(application_mod_path.rsplit('.', 1))
  
  application_class = __import__(application_mod, globals(), locals(), [application_class_name])

  application = application_class()
  trapezewsgi_server = TrapezeWSGI(application, routing_key)
  trapezewsgi_server.serve_forever()

if __name__ == '__main__':
  main()


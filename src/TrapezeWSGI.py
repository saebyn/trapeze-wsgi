from amqplib import client_0_8 as amqp

from wsgiref.handlers import BaseHandler

# TODO do the queue name or the consumer tag need to be unique?
DEFAULT_QUEUE_NAME='app'
DEFAULT_EXCHANGE_NAME='trapeze'
CONSUMER_TAG='consumer'

class TrapezeWSGI:
  def __init__(self, wsgi_handler=BaseHandler):
    pass

  def serve_forever(self):
    try:
      while True:
        pass
    except:
      self._cleanup()

  def handle_request(self):
    pass
    self._cleanup()

  def _cleanup(self):
    pass

ROUTING_KEY='*.localhost.*./.#'

conn = amqp.Connection(host="localhost:5672 ", userid="guest", password="guest", virtual_host="/", insist=False)
chan = conn.channel()

chan.queue_declare(queue=DEFAULT_QUEUE_NAME, durable=False, exclusive=False, auto_delete=False)
chan.queue_bind(queue=DEFAULT_QUEUE_NAME, exchange=DEFAULT_EXCHANGE_NAME, routing_key=ROUTING_KEY)

def recv_callback(msg):
  print 'Recv: ' + msg.body
  response = amqp.Message("HTTP/1.1 200 OK\r\nDate: Fri, 31 Dec 1999 23:59:59 GMT\r\nContent-Length: 112\r\nContent-Type: text/plain\r\n\r\nHi World\n", correlation_id=msg.message_id)
  # don't ack until after wsgi app returns response and we are just about to send that back to the queue.
  chan.basic_ack(msg.delivery_tag)
  chan.basic_publish(response, routing_key=msg.reply_to)

chan.basic_consume(queue=DEFAULT_QUEUE_NAME, callback=recv_callback, consumer_tag=CONSUMER_TAG, no_ack=True)

while True:
  chan.wait()

chan.basic_cancel(CONSUMER_TAG)


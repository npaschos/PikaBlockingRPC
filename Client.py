import pika
import uuid
import time  # to implement a timeout functionality


class BlockingClient(object):
    '''
    Simple Client class that handles the connection and RPC
    logic of a queue.
    args:
      publish_queue   : (str) - default exchange is used so this is the queue name
      host            : (str) - host of the rabbit instance
      timeout         : (int) - timeout in seconds
    '''

    def __init__(self,
                 publish_queue='publish_lost',
                 host='rabbit',
                 exclusive=False,
                 timeout=60,
                 *args,
                 **kwargs):

        self.timeout = timeout
        self.host = host
        self.exclusive = exclusive
        self.publish_queue = publish_queue

        # Basic rabbit connection
        params = pika.ConnectionParameters(host=self.host)
        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

        # publish_queue is used to forward to the correct queue,
        # since the default exchange is used
        result = self.channel.queue_declare('amq.rabbitmq.reply-to',
                                            exclusive=self.exclusive)

        self.channel.basic_consume(queue='amq.rabbitmq.reply-to',
                                   auto_ack=True,
                                   on_message_callback=self._on_response)

        return super().__init__(*args, **kwargs)

    # This is called whenever a response gets in the queue
    def _on_response(self, ch, method, props, body):
        '''
        Internal function used to read the response.
        Not to be ever used explicitly.
        '''
        # print("self is {} and props is {}".format(self.corr_id,
        #                                           props.correlation_id))
        if self.corr_id == props.correlation_id:
            self.response = body

    # Used to post a message
    def call(self, message="Hello World!"):
        '''
        Post a message to the queue and wait for its response
        '''
        self.response = None
        self.corr_id = str(uuid.uuid4())
        props = pika.BasicProperties(
            reply_to='amq.rabbitmq.reply-to',
            correlation_id=self.corr_id,
        )
        self.channel.basic_publish(exchange='',
                                   routing_key=self.publish_queue,
                                   properties=props,
                                   body=message)

        for i in range(8 * self.timeout):
            if self.response is None:
                self.connection.process_data_events()
            else:
                break
            time.sleep(0.125)
        else:
            print("MISSED: {}".format(self.corr_id))
            return "Connection timeout - 504"
        return self.response

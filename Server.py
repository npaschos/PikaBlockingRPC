import pika


class BlockingServer(object):
    def __init__(self,
                 host='rabbit',
                 consume_queue='consume_lost',
                 timeout=60,
                 prefetch_count=1,
                 process=None,
                 *args,
                 **kwargs):

        self.host = host
        self.consume_queue = consume_queue
        self.timeout = timeout
        self.prefetch_count = prefetch_count

        self.process = process

        params = pika.ConnectionParameters(
            host=self.host, blocked_connection_timeout=self.timeout)
        connection = pika.BlockingConnection(params)

        self.channel = connection.channel()

        self.channel.queue_declare(queue=self.consume_queue)
        self.channel.basic_consume(queue=self.consume_queue,
                                   on_message_callback=self._on_request)
        self.channel.basic_qos(prefetch_count=self.prefetch_count)

        return super().__init__(*args, **kwargs)

    def _on_request(self, ch, method, props, body):
        print(" [.] process(%s)" % body)

        response = self.process(body)
        properties = pika.BasicProperties(correlation_id=props.correlation_id)
        print(props.correlation_id)
        ch.basic_publish(exchange='',
                         routing_key=props.reply_to,
                         properties=properties,
                         body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print("Done")

    def consume(self, queue=''):

        print(" [x] Awaiting RPC requests")
        self.channel.start_consuming()


# Example process function
def fib(n):
    n = int(n)
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)
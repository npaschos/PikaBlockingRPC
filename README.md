# PikaBlockingRPC
This is a repo to accompany this [SO post.](https://stackoverflow.com/questions/56003714/rabbitmq-pika-single-rpc-callback-for-multiple-clients)

### Requirements
  - Python 3.6.7
  - pika==1.0.1
  - rabbitmq:3.7.14 (run via [docker](https://hub.docker.com/_/rabbitmq))

**NOTE!** Check the Update section at the bottom of this document for a list of things that have changed and why.

### Code Goals Explained

I followed the official [RabbitMQ Documentation](https://www.rabbitmq.com/tutorials/tutorial-six-python.html) as to how to get started with RabbitMQ and Pika. I wanted to create reuseable code that uses RPC logic with multiple Clients and Servers. The general idea is the following: Multiple Clienrs can publish messages to an exchange (the default is used for now) and only one Server picks it up, processes it and sends a response to a callback queue. The Clients meanwhile looks for responses at the same callback queue. The response is read only when the correlation_id is identified.

### When the code works

Everything runs smoothly when a single Client is used. It does not matter if one or more (I have tried up until 4) Servers are used. The behavior is as expected. Messages are published, consumed once and a response is sent.

### When the code fails (UPDATE: details at the end of this document)

The problem occurs when (even with a single Server) more than one Clients are used. The easiest way to reproduce the issue is with 2 Clients and 1 Server. When one Client publishes a message, the Server picks it up and processes it. When the 2nd Client connects (it is actually the ```channel.basic_consume()``` command that breaks everything) then timeouts start to occur, even though the Server processes the messages correctly.

### Steps to reproduce the issue

Start the docker Rabbit container via 
```sh
$ sudo docker run -p 5672:5672 -d --hostname _rabbit --name rabbit rabbitmq:3
```
Start 1 Server instance. Open a python interactive shell and type:
```python
from Server import BlockingServer, fib
sr = BlockingServer(host='localhost',callback_queue='callback',consume_queue='client',process=fib, prefetch_count=1)
sr.consume()
```
Start 1 Client instance. Open a python interactive shell and type:
```python
from Client import BlockingClient
cl = BlockingClient(host='localhost',publish_queue='client', callback_queue='callback',timeout=3)

while True:
  cl.call('1')
```
At this point everything runs smoothly and messages are being processed. The Server prints the correlation_id it reads.
Open now a 3rd python interactive shell and type the following:
```python
from Client import BlockingClient
cl = BlockingClient(host='localhost',publish_queue='client', callback_queue='callback',timeout=3)

for i in range(20):
  print('iter: {}/20 with response:'.format(i+1))
  cl.call('2')
```
You will instantly notice that timeouts occur instantly. After the 20 iterations of the 2nd Client finish and the Client timeouts (due to lack of a heartbeat) the 1st Server returns to the normal behavior.
___
I then tried a step by step approach and instead of the 2nd Client I used the following commands:
```python
import pika

def on_resp(*args, **kwargs):
  print("I have returned, father")

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
result = channel.queue_declare('callback')

# this breaks everything
channel.basic_consume(queue='callback',on_message_callback=on_resp)
while True:
  connection.process_data_events()
```
As the comment suggests, the `channel.basic_consume()` is when the trouble begins.
___
___
### UPDATE
After  investigating the [direct reply-to](https://www.rabbitmq.com/direct-reply-to.html) functionality of RabbitMQ I removed the explicit decleration of a `callback_queue` and instead now always use the `amq.rabbitmq.reply-to` "queue". Necessary changes were made to both Client and Server classes and the problems described above seem to be resolved. **I do not however understand why this works and the previous logic failed to produce the results I expected.**

### Possible Future Work
Transform this project into a robust RPC example with a detailed documentation explaining how everything works and why some decisions were made.

### NonBlocking Connection?
Now that this version is working some other issues were discovered, regarding the stability of the system. I now understand that a Blocking Connection may not be the best choice, but it is a solid start that helps properly graps the basic concepts. I would love to either expand this example to a RPC system with reconnect capabilities and/or create a NonBlocking Connection robust example.

#### Feel free to comment on these thoughts and changes, all feedback is greatly appreciated.
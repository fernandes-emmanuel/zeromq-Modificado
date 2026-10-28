import os

HOST = os.getenv("ZMQ_HOST", "localhost")

BIND_HOST = os.getenv("ZMQ_BIND_HOST", "*")

PORT1 = os.getenv("ZMQ_PORT1", "4567")
PORT2 = os.getenv("ZMQ_PORT2", "4568")

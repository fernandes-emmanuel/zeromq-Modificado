import os

HOST = os.getenv("ZMQ_HOST", "localhost")      # onde o subscriber conecta
BIND_HOST = os.getenv("ZMQ_BIND_HOST", "*")    # onde o publisher faz bind
PORT = os.getenv("ZMQ_PORT", "4567")

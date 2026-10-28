import os

SRC1  = os.getenv("ZMQ_SRC1", "localhost")    # host da fonte de tarefas 1
SRC2  = os.getenv("ZMQ_SRC2", "localhost")    # host da fonte de tarefas 2
SINK  = os.getenv("ZMQ_SINK", "localhost")    # host do coletor de resultados (novo)
BIND_HOST = os.getenv("ZMQ_BIND_HOST", "*")

PORT1 = os.getenv("ZMQ_PORT1", "4567")        # porta da fonte 1 (fonte N usa 4567+N-1)
PORT2 = os.getenv("ZMQ_PORT2", "4568")        # porta da fonte 2
SINK_PORT = os.getenv("ZMQ_SINK_PORT", "5558")  # resultados: workers -> sink (PUSH/PULL)
CTRL_PORT = os.getenv("ZMQ_CTRL_PORT", "5559")  # controle: sink -> workers (PUB/SUB)


def source_port(me):
	"""Fonte 1 -> PORT1, fonte 2 -> PORT2, fonte N -> PORT1 + N - 1."""
	if str(me) == "1":
		return PORT1
	if str(me) == "2":
		return PORT2
	return str(int(PORT1) + int(me) - 1)

"""Servidor REQ/REP (Fig. 4.21) com comandos, estatisticas e STOP com senha."""
import argparse, ast, json, operator, socket, time
import zmq
from constCS import *  #-

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
       ast.Mod: operator.mod, ast.Pow: operator.pow,
       ast.USub: operator.neg, ast.UAdd: operator.pos}

def calc(expr):
	def ev(node):
		if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
			return node.value
		if isinstance(node, ast.BinOp) and type(node.op) in OPS:
			if isinstance(node.op, ast.Pow) and abs(ev(node.right)) > 100:
				raise ValueError("expoente muito grande")
			return OPS[type(node.op)](ev(node.left), ev(node.right))
		if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
			return OPS[type(node.op)](ev(node.operand))
		raise ValueError("expressao invalida")
	return ev(ast.parse(expr, mode="eval").body)


class Server:
	def __init__(self, token=None):
		self.token = token
		self.start = time.time()
		self.total = 0
		self.by_cmd = {}
		self.by_client = {}
		self.running = True

	def handle(self, req):
		cmd = str(req.get("cmd", "ECHO")).upper()
		arg = req.get("arg", "")
		client = req.get("client", "?")
		self.total += 1
		self.by_cmd[cmd] = self.by_cmd.get(cmd, 0) + 1
		self.by_client[client] = self.by_client.get(client, 0) + 1

		if cmd == "ECHO":
			return {"ok": True, "result": str(arg) + "*"}
		if cmd == "UPPER":
			return {"ok": True, "result": str(arg).upper()}
		if cmd == "REVERSE":
			return {"ok": True, "result": str(arg)[::-1]}
		if cmd == "TIME":
			return {"ok": True, "result": time.asctime()}
		if cmd == "CALC":
			try:
				return {"ok": True, "result": calc(str(arg))}
			except Exception as e:
				return {"ok": False, "error": "CALC: %s" % e}
		if cmd == "INFO":
			return {"ok": True, "result": {"host": socket.gethostname(),
			        "ip": local_ip(), "ports": [PORT1, PORT2]}}
		if cmd == "STATS":
			return {"ok": True, "result": {"uptime_s": round(time.time() - self.start, 1),
			        "total": self.total, "by_cmd": self.by_cmd, "by_client": self.by_client}}
		if cmd == "STOP":
			if self.token and arg != self.token:
				return {"ok": False, "error": "STOP: senha incorreta"}
			self.running = False
			return {"ok": True, "result": "servidor encerrando"}
		return {"ok": False, "error": "comando desconhecido: " + cmd}


def local_ip():
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("10.255.255.255", 1))
		ip = s.getsockname()[0]
		s.close()
		return ip
	except OSError:
		return "127.0.0.1"


def log(msg):
	print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def main():
	ap = argparse.ArgumentParser(description="Servidor ZeroMQ REQ/REP estendido")
	ap.add_argument("--bind", default=BIND_HOST, help="interface de bind (padrao: *)")
	ap.add_argument("--ports", nargs="+", default=[PORT1, PORT2])
	ap.add_argument("--token", default=None, help="senha exigida pelo comando STOP")
	ap.add_argument("--quiet", action="store_true", help="nao loga cada requisicao")
	args = ap.parse_args()

	context = zmq.Context()
	s = context.socket(zmq.REP)               # create reply socket
	for port in args.ports:
		s.bind("tcp://%s:%s" % (args.bind, port))  # bind socket to address
	log("servidor %s (%s) escutando nas portas %s" % (socket.gethostname(), local_ip(), ", ".join(args.ports)))

	srv = Server(args.token)
	while srv.running:
		msg = s.recv()                          # wait for incoming message
		decoded_msg = bytes.decode(msg)
		try:
			req = json.loads(decoded_msg)
			if not isinstance(req, dict):
				raise ValueError
		except ValueError:
			if "STOP" in decoded_msg:
				log("STOP (texto puro) recebido, encerrando")
				break
			srv.handle({"cmd": "ECHO", "client": "legacy"})
			s.send(str.encode(decoded_msg + "*"))
			log("legacy  -> %r" % decoded_msg)
			continue

		rep = srv.handle(req)
		s.send_string(json.dumps(rep))
		if not args.quiet:
			log("%-15s %-8s %r -> %s" % (req.get("client", "?"), str(req.get("cmd", "")).upper(),
			    req.get("arg", ""), rep.get("result", rep.get("error"))))

	s.close(linger=500)
	context.term()
	log("servidor finalizado. total de requisicoes: %d" % srv.total)


if __name__ == "__main__":
	main()

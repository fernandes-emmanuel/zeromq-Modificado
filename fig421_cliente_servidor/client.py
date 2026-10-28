"""Cliente REQ/REP (Fig. 4.21): modo interativo, timeout/retry e benchmark."""
import argparse, json, socket, statistics, sys, time
import zmq
from constCS import *  #-

HELP = """Comandos: ECHO <txt> | UPPER <txt> | REVERSE <txt> | TIME | CALC <expr>
          INFO | STATS | STOP [senha] | QUIT (sai so do cliente)"""


class Client:
	def __init__(self, host, port, timeout_ms=2000, retries=3):
		self.endpoint = "tcp://%s:%s" % (host, port)  # how and where to connect
		self.timeout_ms = timeout_ms
		self.retries = retries
		self.name = socket.gethostname()
		self.context = zmq.Context()
		self._open()

	def _open(self):
		self.s = self.context.socket(zmq.REQ)        # create request socket
		self.s.setsockopt(zmq.LINGER, 0)
		self.s.connect(self.endpoint)

	def request(self, cmd, arg=""):
		"""Envia um comando e devolve (resposta, rtt_ms). Lanca TimeoutError."""
		payload = json.dumps({"cmd": cmd, "arg": arg, "client": self.name})
		for attempt in range(1, self.retries + 1):
			t0 = time.perf_counter()
			self.s.send_string(payload)
			if self.s.poll(self.timeout_ms, zmq.POLLIN):
				rep = json.loads(self.s.recv_string())
				return rep, (time.perf_counter() - t0) * 1000
			print("  [timeout] sem resposta de %s (tentativa %d/%d)" %
			      (self.endpoint, attempt, self.retries), file=sys.stderr)
			self.s.close()
			self._open()
		raise TimeoutError("servidor %s indisponivel" % self.endpoint)

	def close(self):
		self.s.close()
		self.context.term()


def show(rep, rtt):
	if rep.get("ok"):
		res = rep["result"]
		if isinstance(res, dict):
			res = json.dumps(res, indent=2, ensure_ascii=False)
		print("%s   (%.2f ms)" % (res, rtt))
	else:
		print("ERRO: %s   (%.2f ms)" % (rep.get("error"), rtt))


def bench(c, n):
	rtts = []
	for i in range(n):
		_, rtt = c.request("ECHO", "ping %d" % i)
		rtts.append(rtt)
	rtts.sort()
	print("benchmark %s: %d requisicoes" % (c.endpoint, n))
	print("  media %.3f ms | mediana %.3f ms | min %.3f ms | p95 %.3f ms | max %.3f ms" %
	      (statistics.mean(rtts), statistics.median(rtts), rtts[0],
	       rtts[int(0.95 * (n - 1))], rtts[-1]))
	print("  vazao aprox.: %.0f req/s" % (n / (sum(rtts) / 1000)))


def interactive(c):
	print("Conectado a %s\n%s" % (c.endpoint, HELP))
	while True:
		try:
			line = input("> ").strip()
		except EOFError:
			break
		if not line:
			continue
		cmd, _, arg = line.partition(" ")
		if cmd.upper() in ("QUIT", "EXIT"):
			break
		if cmd.upper() == "HELP":
			print(HELP)
			continue
		try:
			show(*c.request(cmd.upper(), arg))
		except TimeoutError as e:
			print("ERRO:", e)
			break
		if cmd.upper() == "STOP":
			break


def main():
	ap = argparse.ArgumentParser(description="Cliente ZeroMQ REQ/REP estendido")
	ap.add_argument("--host", default=HOST)
	ap.add_argument("--port", default=PORT1)
	ap.add_argument("--timeout", type=int, default=2000, help="timeout em ms")
	ap.add_argument("--retries", type=int, default=3)
	ap.add_argument("--cmd", nargs="+", metavar=("CMD", "ARG"),
	                help="executa um unico comando e sai")
	ap.add_argument("--bench", type=int, metavar="N", help="mede RTT de N requisicoes")
	args = ap.parse_args()

	c = Client(args.host, args.port, args.timeout, args.retries)
	try:
		if args.bench:
			bench(c, args.bench)
		elif args.cmd:
			rep, rtt = c.request(args.cmd[0].upper(), " ".join(args.cmd[1:]))
			show(rep, rtt)
			if not rep.get("ok"):
				sys.exit(1)
		else:
			interactive(c)
	except TimeoutError as e:
		print("ERRO:", e, file=sys.stderr)
		sys.exit(2)
	finally:
		c.close()


if __name__ == "__main__":
	main()

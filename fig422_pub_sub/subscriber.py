"""Subscriber (Fig. 4.22) com filtro de topicos, varios publishers e deteccao de perdas."""
import argparse, json, time
import zmq
from constPS import *  #-


def main():
	ap = argparse.ArgumentParser(description="Subscriber ZeroMQ estendido")
	ap.add_argument("--hosts", nargs="+", default=[HOST], help="publishers (host ou host:porta)")
	ap.add_argument("--port", default=PORT)
	ap.add_argument("--topics", nargs="+", default=["TIME"])
	ap.add_argument("--count", type=int, default=5, help="mensagens a receber (0 = infinito)")
	ap.add_argument("--timeout", type=float, default=0, help="encerra apos N s sem mensagens (0 = nunca)")
	args = ap.parse_args()

	context = zmq.Context()
	s = context.socket(zmq.SUB)                  # create a subscriber socket
	for h in args.hosts:
		ep = "tcp://" + (h if ":" in h else h + ":" + args.port)
		s.connect(ep)                              # connect to the server(s)
		print("conectado a", ep)
	for t in args.topics:
		s.setsockopt_string(zmq.SUBSCRIBE, t)     # subscribe to each topic
	print("assinando topicos:", args.topics, flush=True)

	stats = {}
	received = 0
	try:
		while args.count == 0 or received < args.count:
			if args.timeout and not s.poll(args.timeout * 1000):
				print("nenhuma mensagem em %.0fs, encerrando" % args.timeout)
				break
			parts = s.recv_multipart()
			if len(parts) == 1:
				received += 1
				print("[%s] (original) %s" % (time.strftime("%H:%M:%S"), parts[0].decode()), flush=True)
				continue
			topic, body = parts[0].decode(), json.loads(parts[1])
			received += 1
			delay = (time.time() - body["ts"]) * 1000
			st = stats.setdefault((body["pub"], topic), {"n": 0, "lost": 0, "last": None, "delay": 0.0})
			if st["last"] is not None and body["seq"] > st["last"] + 1:
				st["lost"] += body["seq"] - st["last"] - 1
				print("  !! %d mensagem(ns) perdida(s) de %s/%s" % (body["seq"] - st["last"] - 1, body["pub"], topic))
			st["last"] = body["seq"]
			st["n"] += 1
			st["delay"] += delay
			print("[%s] %-5s #%-4d de %-12s atraso %6.2f ms: %s" %
			      (time.strftime("%H:%M:%S"), topic, body["seq"], body["pub"], delay, body["data"]), flush=True)
	except KeyboardInterrupt:
		pass

	print("\n--- resumo ---")
	for (pub, topic), st in sorted(stats.items()):
		print("%-12s %-5s recebidas=%-4d perdidas=%-3d atraso medio=%.2f ms" %
		      (pub, topic, st["n"], st["lost"], st["delay"] / st["n"]))
	s.close()
	context.term()


if __name__ == "__main__":
	main()

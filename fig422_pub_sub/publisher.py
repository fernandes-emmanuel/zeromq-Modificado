"""Publisher (Fig. 4.22) com varios topicos, chat e numero de sequencia."""
import argparse, json, os, queue, socket, sys, threading, time
import zmq
from constPS import *  #-


def sys_info():
	info = {"cpus": os.cpu_count()}
	try:
		info["loadavg"] = [round(x, 2) for x in os.getloadavg()]
	except OSError:
		pass
	try:
		with open("/proc/meminfo") as f:
			mem = {l.split(":")[0]: int(l.split()[1]) for l in f}
		info["mem_used_pct"] = round(100 * (1 - mem["MemAvailable"] / mem["MemTotal"]), 1)
	except (OSError, KeyError):
		pass
	return info


def stdin_reader(q):
	for line in sys.stdin:
		line = line.strip()
		if line:
			q.put(line)
	q.put(None)


def main():
	ap = argparse.ArgumentParser(description="Publisher ZeroMQ estendido")
	ap.add_argument("--bind", default=BIND_HOST)
	ap.add_argument("--port", default=PORT)
	ap.add_argument("--interval", type=float, default=5.0, help="segundos entre publicacoes")
	ap.add_argument("--topics", nargs="*", default=["TIME", "SYS"], help="topicos periodicos")
	ap.add_argument("--name", default=socket.gethostname(), help="nome deste publisher")
	ap.add_argument("--count", type=int, default=0, help="n. de rodadas (0 = infinito)")
	ap.add_argument("--chat", action="store_true", help="publica linhas digitadas no topico CHAT")
	ap.add_argument("--legacy", action="store_true", help="envia TIME no formato original (Fig. 4.22)")
	args = ap.parse_args()

	context = zmq.Context()
	s = context.socket(zmq.PUB)                     # create a publisher socket
	s.bind("tcp://%s:%s" % (args.bind, args.port))  # bind socket to the address
	print("publisher '%s' em tcp://%s:%s topicos=%s intervalo=%.1fs" %
	      (args.name, args.bind, args.port, args.topics, args.interval), flush=True)

	seq = {}
	def publish(topic, data):
		seq[topic] = seq.get(topic, 0) + 1
		body = {"seq": seq[topic], "pub": args.name, "ts": time.time(), "data": data}
		s.send_multipart([topic.encode(), json.dumps(body).encode()])
		print("-> %-5s #%d %s" % (topic, seq[topic], data), flush=True)

	chat = queue.Queue()
	if args.chat:
		threading.Thread(target=stdin_reader, args=(chat,), daemon=True).start()
		print("digite mensagens para publicar no topico CHAT (Ctrl+D encerra)", flush=True)

	rounds = 0
	next_tick = time.time() + args.interval
	try:
		while args.count == 0 or rounds < args.count:
			try:
				line = chat.get(timeout=max(0, next_tick - time.time()))
				if line is None:
					break
				publish("CHAT", line)
				continue
			except queue.Empty:
				pass
			next_tick += args.interval
			rounds += 1
			for topic in args.topics:
				if topic == "TIME" and args.legacy:
					s.send(str.encode("TIME " + time.asctime()))  # publish the current time
					print("-> TIME  (formato original) " + time.asctime(), flush=True)
				elif topic == "TIME":
					publish("TIME", time.asctime())
				elif topic == "SYS":
					publish("SYS", sys_info())
				else:
					publish(topic, "%s rodada %d" % (topic, rounds))
	except KeyboardInterrupt:
		pass
	finally:
		s.close(linger=1000)
		context.term()


if __name__ == "__main__":
	main()

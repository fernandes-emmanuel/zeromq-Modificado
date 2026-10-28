"""Worker (Fig. 4.23) que envia resultados ao sink e encerra com KILL."""
import argparse, json, socket, time
import zmq
from constPipe import *  #-


def count_primes(n):
	if n < 2:
		return 0
	sieve = bytearray([1]) * (n + 1)
	sieve[0] = sieve[1] = 0
	for i in range(2, int(n ** 0.5) + 1):
		if sieve[i]:
			sieve[i * i::i] = bytearray(len(range(i * i, n + 1, i)))
	return sum(sieve)


def main():
	ap = argparse.ArgumentParser(description="Worker (PULL)")
	ap.add_argument("me", help="nome do worker")
	ap.add_argument("--sources", nargs="+",
	                default=["%s:%s" % (SRC1, PORT1), "%s:%s" % (SRC2, PORT2)])
	ap.add_argument("--sink", default=SINK, help="host do sink ('' para nao usar)")
	ap.add_argument("--mode", choices=["sleep", "cpu"], default="sleep")
	args = ap.parse_args()
	me = "%s@%s" % (args.me, socket.gethostname())

	context = zmq.Context()
	r = context.socket(zmq.PULL)                 # create a pull socket
	for src in args.sources:
		r.connect("tcp://" + src)                  # connect to each task source
	poller = zmq.Poller()
	poller.register(r, zmq.POLLIN)

	out = ctrl = None
	if args.sink:
		out = context.socket(zmq.PUSH)             # results -> sink
		out.connect("tcp://%s:%s" % (args.sink, SINK_PORT))
		ctrl = context.socket(zmq.SUB)             # control <- sink
		ctrl.connect("tcp://%s:%s" % (args.sink, CTRL_PORT))
		ctrl.setsockopt_string(zmq.SUBSCRIBE, "KILL")
		poller.register(ctrl, zmq.POLLIN)

	print(me + " started, fontes: " + ", ".join(args.sources), flush=True)
	done = 0
	try:
		while True:
			events = dict(poller.poll())
			if ctrl in events:
				ctrl.recv()
				print(me + ": KILL recebido do sink, encerrando", flush=True)
				break
			if r not in events:
				continue
			work = json.loads(r.recv_string())     # receive work from a source
			print("%s received %3d from %s (%s)" % (me, work["workload"], work["src"], work["task"]), flush=True)
			t0 = time.perf_counter()
			if args.mode == "cpu":
				result = count_primes(work["workload"] * 1000)
			else:
				time.sleep(work["workload"] * 0.01)  # pretend to work
				result = None
			done += 1
			if out:
				work.update(worker=me, result=result, type="result",
				            elapsed=time.perf_counter() - t0)
				out.send_string(json.dumps(work))
	except KeyboardInterrupt:
		pass
	print("%s: %d tarefas processadas" % (me, done), flush=True)
	context.destroy(linger=1000)


if __name__ == "__main__":
	main()

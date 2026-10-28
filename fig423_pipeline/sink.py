"""Sink: coleta resultados dos workers, gera relatorio e encerra os workers."""
import argparse, json, time
import zmq
from constPipe import *  #-


def main():
	ap = argparse.ArgumentParser(description="Sink do pipeline")
	ap.add_argument("--sources", type=int, default=2, help="numero de fontes esperadas")
	ap.add_argument("--quiet", action="store_true")
	args = ap.parse_args()

	context = zmq.Context()
	r = context.socket(zmq.PULL)
	r.bind("tcp://%s:%s" % (BIND_HOST, SINK_PORT))
	ctrl = context.socket(zmq.PUB)
	ctrl.bind("tcp://%s:%s" % (BIND_HOST, CTRL_PORT))
	print("sink: resultados em :%s, controle em :%s, aguardando %d fontes" %
	      (SINK_PORT, CTRL_PORT, args.sources), flush=True)

	expected = {}
	got = 0
	per_worker = {}
	per_source = {}
	t0 = None
	while len(expected) < args.sources or got < sum(expected.values()):
		msg = json.loads(r.recv_string())
		if t0 is None:
			t0 = time.time()
		if msg["type"] == "start":
			expected[msg["src"]] = msg["tasks"]
			print("sink: fonte %s anunciou %d tarefas" % (msg["src"], msg["tasks"]), flush=True)
			continue
		got += 1
		w = per_worker.setdefault(msg["worker"], [0, 0.0, 0])
		w[0] += 1
		w[1] += msg["elapsed"]
		w[2] += msg["workload"]
		per_source[msg["src"]] = per_source.get(msg["src"], 0) + 1
		if not args.quiet:
			res = "" if msg["result"] is None else " -> %d primos" % msg["result"]
			print("sink: %-8s feita por %s (%.3fs)%s [%d/%s]" %
			      (msg["task"], msg["worker"], msg["elapsed"], res, got,
			       sum(expected.values()) if len(expected) == args.sources else "?"), flush=True)

	total = time.time() - t0
	print("\n===== relatorio do pipeline =====")
	print("tarefas: %d em %.2fs (%.1f tarefas/s)" % (got, total, got / total))
	print("por fonte: " + ", ".join("%s=%d" % kv for kv in sorted(per_source.items())))
	print("%-28s %8s %8s %12s %10s" % ("worker", "tarefas", "%", "ocupado(s)", "workload"))
	for name, (n, busy, wl) in sorted(per_worker.items()):
		print("%-28s %8d %7.1f%% %12.2f %10d" % (name, n, 100.0 * n / got, busy, wl))

	for _ in range(3):
		ctrl.send_string("KILL")
		time.sleep(0.2)
	context.destroy(linger=500)


if __name__ == "__main__":
	main()

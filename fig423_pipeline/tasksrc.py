"""Fonte de tarefas (Fig. 4.23)."""
import argparse, json, random, time
import zmq
from constPipe import *  #-


def main():
	ap = argparse.ArgumentParser(description="Fonte de tarefas (PUSH)")
	ap.add_argument("me", help="identificador da fonte (1, 2, ...)")
	ap.add_argument("--tasks", type=int, default=100)
	ap.add_argument("--interval", type=float, default=1.0, help="segundos entre tarefas")
	ap.add_argument("--min", type=int, default=1)
	ap.add_argument("--max", type=int, default=100)
	ap.add_argument("--sink", default=SINK, help="host do sink ('' para nao usar)")
	ap.add_argument("--wait", type=float, default=1.0, help="espera inicial p/ workers conectarem")
	args = ap.parse_args()
	me = args.me

	context = zmq.Context()
	s = context.socket(zmq.PUSH)               # create a push socket
	prt = source_port(me)
	s.bind("tcp://%s:%s" % (BIND_HOST, prt))   # bind socket to address
	print("fonte %s: tcp://%s:%s, %d tarefas" % (me, BIND_HOST, prt, args.tasks), flush=True)

	if args.sink:
		sink = context.socket(zmq.PUSH)
		sink.connect("tcp://%s:%s" % (args.sink, SINK_PORT))
		sink.send_string(json.dumps({"type": "start", "src": me, "tasks": args.tasks}))

	time.sleep(args.wait)
	t0 = time.time()
	for i in range(args.tasks):                    # generate workloads
		workload = random.randint(args.min, args.max)  # compute workload
		task = {"src": me, "task": "%s-%d" % (me, i), "workload": workload}
		s.send_string(json.dumps(task))            # send workload to worker
		time.sleep(args.interval)

	print("fonte %s: %d tarefas enviadas em %.1fs" % (me, args.tasks, time.time() - t0), flush=True)
	s.close(linger=-1)
	if args.sink:
		sink.close(linger=-1)
	context.term()


if __name__ == "__main__":
	main()

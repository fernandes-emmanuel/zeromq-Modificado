#!/usr/bin/env bash
# Simula "maquinas diferentes" com containers Docker, cada um com seu
# proprio hostname e IP numa rede 172.28.0.0/16, e roda os tres exemplos
# (originais e estendidos). Os logs vao para resultados/.
#
# Uso (na raiz do repositorio):  bash docker/teste_multihost.sh
set -u
cd "$(dirname "$0")/.."
ROOT=$(pwd)
OUT=$ROOT/resultados
IMAGE=${IMAGE:-zmq-lab}
NET=zmqnet
mkdir -p "$OUT"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
	docker build -t "$IMAGE" -f docker/Dockerfile .
fi
docker network inspect $NET >/dev/null 2>&1 || docker network create --subnet 172.28.0.0/16 $NET >/dev/null

# run <nome> <ip> <diretorio> <comando...>   (em background)
run() {
	local name=$1 ip=$2 dir=$3; shift 3
	docker rm -f "$name" >/dev/null 2>&1
	docker run -d --name "$name" --hostname "$name" --network $NET --ip "$ip" \
		-v "$ROOT":/app:ro -w "/app/$dir" -e PYTHONUNBUFFERED=1 "$IMAGE" "$@" >/dev/null
}
# exec_fg <nome> <ip> <diretorio> <comando...>   (em primeiro plano, mostra a saida)
exec_fg() {
	local name=$1 ip=$2 dir=$3; shift 3
	docker rm -f "$name" >/dev/null 2>&1
	docker run --rm -i --name "$name" --hostname "$name" --network $NET --ip "$ip" \
		-v "$ROOT":/app:ro -w "/app/$dir" -e PYTHONUNBUFFERED=1 "$IMAGE" "$@"
}
logs() { docker logs "$1" 2>&1; }
cleanup() { docker rm -f $(docker ps -aq --filter network=$NET) >/dev/null 2>&1; }
cleanup

########################################################################
echo "### Fig. 4.21 ORIGINAL (servidor 172.28.0.10, clientes em outros hosts)"
# o codigo original tem o IP fixo 172.31.18.70; trocamos so o IP numa copia
TMP=$(mktemp -d); cp -r original "$TMP/"; chmod -R a+rX "$TMP"
sed -i 's/172.31.18.70/172.28.0.10/' "$TMP"/original/*/const*.py
sed -i 's/172.31.16.33/172.28.0.31/' "$TMP"/original/*/const*.py
docker rm -f srv-orig >/dev/null 2>&1
docker run -d --name srv-orig --hostname servidor --network $NET --ip 172.28.0.10 \
	-v "$TMP":/orig:ro -w /orig/original/fig-4.21-cliente-servidor "$IMAGE" python3 server.py >/dev/null
sleep 1
{
	echo "cliente1 (172.28.0.11) -> porta 4567:"
	docker run --rm --network $NET --ip 172.28.0.11 -v "$TMP":/orig:ro -w /orig/original/fig-4.21-cliente-servidor "$IMAGE" python3 client1.py
	echo "cliente2 (172.28.0.12) -> porta 4568:"
	docker run --rm --network $NET --ip 172.28.0.12 -v "$TMP":/orig:ro -w /orig/original/fig-4.21-cliente-servidor "$IMAGE" python3 client2.py
	echo "client.py (envia STOP):"
	docker run --rm --network $NET --ip 172.28.0.11 -v "$TMP":/orig:ro -w /orig/original/fig-4.21-cliente-servidor "$IMAGE" python3 client.py
} 2>&1 | tee "$OUT/fig421_original.txt"
sleep 1; docker rm -f srv-orig >/dev/null

########################################################################
echo; echo "### Fig. 4.21 ESTENDIDO"
D=fig421_cliente_servidor
run servidor 172.28.0.10 $D python3 server.py --token segredo
sleep 1
{
	echo "== cliente1 (172.28.0.11): comandos unicos"
	for c in "ECHO Hello world 1" "UPPER sistemas distribuidos" "REVERSE zeromq" "CALC (2+3)*7**2" "CALC __import__('os')" "TIME" "INFO"; do
		echo "\$ client.py --host 172.28.0.10 --cmd $c"
		exec_fg cliente1 172.28.0.11 $D python3 client.py --host 172.28.0.10 --cmd $c
	done
	echo; echo "== cliente2 (172.28.0.12): modo interativo pela porta 4568"
	printf 'ECHO Hello world 2\nCALC 10/4\nSTATS\nQUIT\n' | exec_fg cliente2 172.28.0.12 $D python3 client.py --host 172.28.0.10 --port 4568
	echo; echo "== cliente original (texto puro) falando com o servidor estendido"
	docker run --rm --network $NET --ip 172.28.0.13 -v "$TMP":/orig:ro -w /orig/original/fig-4.21-cliente-servidor "$IMAGE" python3 client1.py
	echo; echo "== benchmark de outro host (1000 requisicoes)"
	exec_fg cliente1 172.28.0.11 $D python3 client.py --host 172.28.0.10 --bench 1000
	echo; echo "== STOP com senha errada e depois correta"
	exec_fg cliente1 172.28.0.11 $D python3 client.py --host 172.28.0.10 --cmd STOP errada
	exec_fg cliente1 172.28.0.11 $D python3 client.py --host 172.28.0.10 --cmd STOP segredo
	sleep 1
	echo; echo "== servidor fora do ar: timeout + novas tentativas"
	exec_fg cliente1 172.28.0.11 $D python3 client.py --host 172.28.0.10 --timeout 500 --retries 3 --cmd TIME
	echo "codigo de saida: $?"
} 2>&1 | tee "$OUT/fig421_estendido_clientes.txt"
logs servidor | grep -v "ping " > "$OUT/fig421_estendido_servidor.txt"
echo "--- log do servidor (sem as linhas do benchmark):"; cat "$OUT/fig421_estendido_servidor.txt"
docker rm -f servidor >/dev/null

########################################################################
echo; echo "### Fig. 4.22 ORIGINAL"
docker run -d --name pub-orig --hostname publisher --network $NET --ip 172.28.0.10 \
	-v "$TMP":/orig:ro -w /orig/original/fig-4.22-pub-sub "$IMAGE" python3 publisher.py >/dev/null
docker run --rm --network $NET --ip 172.28.0.11 -v "$TMP":/orig:ro -w /orig/original/fig-4.22-pub-sub \
	"$IMAGE" python3 subscriber.py 2>&1 | tee "$OUT/fig422_original.txt"
docker rm -f pub-orig >/dev/null

echo; echo "### Fig. 4.22 ESTENDIDO (3 publishers, 4 subscribers)"
D=fig422_pub_sub
run pub1 172.28.0.20 $D python3 publisher.py --interval 1 --count 12 --legacy
run pub2 172.28.0.21 $D python3 publisher.py --interval 1 --count 12 --topics TIME SYS NEWS
run sub1 172.28.0.22 $D python3 subscriber.py --hosts 172.28.0.20 172.28.0.21 --topics TIME --count 6
run sub2 172.28.0.23 $D python3 subscriber.py --hosts 172.28.0.20 172.28.0.21 --topics SYS NEWS --count 10
# subscriber original (Fig. 4.22) recebendo do publisher estendido (pub1)
mkdir -p "$TMP/suborig"; cp original/fig-4.22-pub-sub/*.py "$TMP/suborig/"
sed -i 's/172.31.18.70/172.28.0.20/' "$TMP/suborig/constPS.py"; chmod -R a+rX "$TMP"
docker rm -f sub-orig >/dev/null 2>&1
docker run -d --name sub-orig --network $NET --ip 172.28.0.24 -e PYTHONUNBUFFERED=1 -v "$TMP":/orig:ro \
	-w /orig/suborig "$IMAGE" python3 subscriber.py >/dev/null
# CHAT: publisher interativo recebendo linhas pelo stdin
docker rm -f pub3 >/dev/null 2>&1
( sleep 3; echo "ola de outra maquina!"; sleep 1; echo "ZeroMQ PUB/SUB funcionando"; sleep 3 ) | \
	docker run -i --rm --name pub3 --hostname pub3 --network $NET --ip 172.28.0.25 -v "$ROOT":/app:ro \
	-w /app/$D -e PYTHONUNBUFFERED=1 "$IMAGE" python3 publisher.py --chat --topics > "$OUT/fig422_chat_publisher.txt" 2>&1 &
run sub3 172.28.0.26 $D python3 subscriber.py --hosts 172.28.0.25 --topics CHAT --count 2 --timeout 20
sleep 14
for c in pub1 pub2 sub1 sub2 sub-orig sub3; do
	echo "----- $c" ; logs $c
done 2>&1 | tee "$OUT/fig422_estendido.txt"
wait
docker rm -f pub1 pub2 sub1 sub2 sub-orig sub3 >/dev/null 2>&1

########################################################################
echo; echo "### Fig. 4.23 ORIGINAL (2 fontes, 2 workers; 10s de amostra)"
docker rm -f src1-o src2-o w1-o w2-o >/dev/null 2>&1
for s in "src1-o 172.28.0.10 tasksrc.py 1" "src2-o 172.28.0.31 tasksrc.py 2" "w1-o 172.28.0.40 taskwork.py A" "w2-o 172.28.0.41 taskwork.py B"; do
	set -- $s
	docker run -d --name $1 --hostname $1 --network $NET --ip $2 -e PYTHONUNBUFFERED=1 -v "$TMP":/orig:ro \
		-w /orig/original/fig-4.23-pipeline "$IMAGE" python3 -u $3 $4 >/dev/null
done
sleep 10
{ echo "----- worker A"; logs w1-o; echo "----- worker B"; logs w2-o; } | tee "$OUT/fig423_original.txt"
docker rm -f src1-o src2-o w1-o w2-o >/dev/null

echo; echo "### Fig. 4.23 ESTENDIDO (2 fontes, 3 workers, 1 sink)"
D=fig423_pipeline
ENV="-e ZMQ_SRC1=172.28.0.30 -e ZMQ_SRC2=172.28.0.31 -e ZMQ_SINK=172.28.0.32"
runp() { local n=$1 ip=$2; shift 2; docker rm -f $n >/dev/null 2>&1
	docker run -d --name $n --hostname $n --network $NET --ip $ip $ENV -e PYTHONUNBUFFERED=1 \
		-v "$ROOT":/app:ro -w /app/$D "$IMAGE" "$@" >/dev/null; }
runp sink    172.28.0.32 python3 sink.py --sources 2
runp worker1 172.28.0.40 python3 taskwork.py A --mode cpu
runp worker2 172.28.0.41 python3 taskwork.py B --mode cpu
runp worker3 172.28.0.42 python3 taskwork.py C --mode sleep
sleep 1
runp fonte1  172.28.0.30 python3 tasksrc.py 1 --tasks 40 --interval 0.05
runp fonte2  172.28.0.31 python3 tasksrc.py 2 --tasks 40 --interval 0.05
docker wait sink >/dev/null; sleep 2
for c in fonte1 fonte2 worker1 worker2 worker3 sink; do
	echo "----- $c"; logs $c
done 2>&1 | tee "$OUT/fig423_estendido.txt"
docker rm -f sink worker1 worker2 worker3 fonte1 fonte2 >/dev/null 2>&1

rm -rf "$TMP"
echo; echo "logs salvos em $OUT/"

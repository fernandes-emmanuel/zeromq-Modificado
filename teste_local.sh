#!/usr/bin/env bash
# Teste rapido dos tres exemplos estendidos numa unica maquina (localhost).
# Uso:  bash teste_local.sh      (com o venv ativado e pyzmq instalado)
set -u
cd "$(dirname "$0")"
PY=${PY:-python3}

echo "### Fig. 4.21 - cliente/servidor"
cd fig421_cliente_servidor
$PY server.py --quiet & SRV=$!
sleep 1
$PY client.py --cmd ECHO "Hello world 1"
$PY client.py --port 4568 --cmd CALC "2**10 + 1"
$PY client.py --bench 200
$PY client.py --cmd STOP
wait $SRV
cd ..

echo; echo "### Fig. 4.22 - publish/subscribe"
cd fig422_pub_sub
$PY publisher.py --interval 0.5 --count 6 > /dev/null & PUB=$!
$PY subscriber.py --topics TIME SYS --count 6
wait $PUB
cd ..

echo; echo "### Fig. 4.23 - pipeline (2 fontes, 2 workers, sink)"
cd fig423_pipeline
$PY sink.py --sources 2 --quiet & SINK=$!
$PY taskwork.py A --mode cpu > /dev/null &
$PY taskwork.py B --mode sleep > /dev/null &
$PY tasksrc.py 1 --tasks 20 --interval 0.02 > /dev/null &
$PY tasksrc.py 2 --tasks 20 --interval 0.02 > /dev/null &
wait $SINK
sleep 1
echo; echo "ok"

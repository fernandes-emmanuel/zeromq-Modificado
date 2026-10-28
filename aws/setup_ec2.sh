#!/usr/bin/env bash
# Prepara uma instancia EC2 (Ubuntu ou Amazon Linux) para rodar os exemplos.
# Pode ser executado via SSH ou colado em "User data" ao criar a instancia.
#
#   bash setup_ec2.sh https://github.com/<usuario>/<repositorio>.git
set -e
REPO=${1:-${REPO_URL:-}}
if [ -z "$REPO" ]; then
	echo "uso: $0 <url-do-repositorio>"; exit 1
fi

if command -v apt-get >/dev/null; then
	sudo apt-get update -y
	sudo apt-get install -y python3 python3-venv python3-pip git
else
	sudo dnf install -y python3 python3-pip git
fi

DIR=$HOME/$(basename "$REPO" .git)
[ -d "$DIR" ] || git clone "$REPO" "$DIR"
cd "$DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python -c "import zmq; print('pyzmq', zmq.__version__, '| libzmq', zmq.zmq_version())"
echo
echo "Pronto. Use:  cd $DIR && source venv/bin/activate"
echo "IP privado desta maquina: $(hostname -I 2>/dev/null | awk '{print $1}')"

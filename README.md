# ZeroMQ em máquinas diferentes — Figs. 4.21, 4.22 e 4.23 (versão estendida)

Trabalho baseado nos exemplos do Capítulo 4 de *Distributed Systems* (van Steen & Tanenbaum),
que usam o middleware **ZeroMQ** (`pyzmq`) para os três padrões clássicos de comunicação:

| Figura | Padrão | Código original | Versão estendida |
|---|---|---|---|
| 4.21 | Cliente-servidor (**REQ/REP**) | [`original/fig-4.21-cliente-servidor`](original/fig-4.21-cliente-servidor) | [`fig421_cliente_servidor`](fig421_cliente_servidor) |
| 4.22 | Publish-subscribe (**PUB/SUB**) | [`original/fig-4.22-pub-sub`](original/fig-4.22-pub-sub) | [`fig422_pub_sub`](fig422_pub_sub) |
| 4.23 | Pipeline (**PUSH/PULL**) | [`original/fig-4.23-pipeline`](original/fig-4.23-pipeline) | [`fig423_pipeline`](fig423_pipeline) |

> No `.zip` fornecido as pastas se chamam `04-22`, `04-23` e `04-24`; elas correspondem,
> respectivamente, às Figs. 4.21, 4.22 e 4.23. O código original foi mantido sem alterações
> em [`original/`](original).

O trabalho consiste em (1) executar os exemplos em **máquinas diferentes** e (2) **acrescentar
novas funcionalidades** às aplicações.

---

## Sumário

1. [Estrutura do repositório](#estrutura-do-repositório)
2. [Instalação (venv + pyzmq)](#instalação)
3. [Novas funcionalidades](#novas-funcionalidades)
4. [Como executar](#como-executar)
5. [Implantação na AWS](#implantação-na-aws)
6. [Testes realizados e resultados](#testes-realizados-e-resultados)
7. [Observações e problemas encontrados](#observações-e-problemas-encontrados)

---

## Estrutura do repositório

```
.
├── original/                      # código-fonte original (Figs. 4.21, 4.22, 4.23), sem alterações
├── fig421_cliente_servidor/       # REQ/REP estendido
│   ├── constCS.py                 #   configuração (variáveis de ambiente)
│   ├── server.py
│   └── client.py
├── fig422_pub_sub/                # PUB/SUB estendido
│   ├── constPS.py
│   ├── publisher.py
│   └── subscriber.py
├── fig423_pipeline/               # PUSH/PULL estendido
│   ├── constPipe.py
│   ├── tasksrc.py                 #   fonte de tarefas
│   ├── taskwork.py                #   worker
│   └── sink.py                    #   NOVO: coletor de resultados
├── aws/setup_ec2.sh               # prepara uma instância EC2 (git, venv, pyzmq)
├── docker/                        # teste "multi-máquina" com containers (um IP por componente)
│   ├── Dockerfile
│   └── teste_multihost.sh
├── resultados/                    # saídas reais dos testes multi-host
├── teste_local.sh                 # teste rápido de tudo em localhost
└── requirements.txt               # pyzmq
```

## Instalação

Em **cada** máquina que for rodar algum componente:

```bash
git clone https://github.com/fernandes-emmanuel/zeromq-Modificado.git
cd zeromq-Modificado
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt   # instala o pyzmq (biblioteca do ZeroMQ)
```

Teste rápido de tudo numa máquina só:

```bash
bash teste_local.sh
```

## Novas funcionalidades

### Comum aos três exemplos

- **Endereços configuráveis** por argumentos de linha de comando ou variáveis de ambiente
  (`ZMQ_HOST`, `ZMQ_PORT`, `ZMQ_SRC1`, `ZMQ_SINK`, ...). No original o IP
  `172.31.18.70` estava fixo no código.
- **Bind em todas as interfaces (`*`)** nos lados que fazem `bind`. Isso é necessário na AWS:
  o IP público não existe na interface de rede da VM, então `bind` no IP público falha.
- Logs com horário, hostname e IP de quem enviou, para deixar visível que a comunicação
  está ocorrendo **entre máquinas diferentes**.
- **Compatibilidade com o código original**: os clientes/assinantes originais continuam
  funcionando com os servidores/publishers novos (testado — ver [resultados](#testes-realizados-e-resultados)).

### Fig. 4.21 — Cliente-servidor (REQ/REP)

| Funcionalidade | Descrição |
|---|---|
| Protocolo com comandos (JSON) | `ECHO` (comportamento original: devolve o texto + `*`), `UPPER`, `REVERSE`, `TIME`, `CALC` (calculadora segura, sem `eval`), `INFO` (hostname/IP do servidor), `STATS`, `STOP` |
| Estatísticas no servidor | `STATS` devolve uptime, total de requisições, contagem por comando e **por cliente (hostname)** |
| `STOP` protegido | `server.py --token segredo` faz o `STOP` exigir senha — no original, qualquer cliente derrubava o servidor |
| Cliente interativo | `client.py` sem argumentos abre um prompt para enviar vários comandos |
| Timeout + novas tentativas | Padrão *Lazy Pirate*: se o servidor não responde em `--timeout` ms, o socket REQ é recriado e a requisição reenviada (`--retries`). No original o cliente travava para sempre |
| Medição de RTT e benchmark | Cada resposta mostra o tempo de ida e volta; `--bench N` mede média/mediana/p95/vazão — útil para comparar mesma máquina × máquinas diferentes |
| Compatibilidade | Mensagens de texto puro (cliente original) recebem a resposta original (`texto*`); `STOP` em texto puro encerra o servidor |

### Fig. 4.22 — Publish-subscribe (PUB/SUB)

| Funcionalidade | Descrição |
|---|---|
| Vários tópicos | `TIME` (original), `SYS` (carga, nº de CPUs e uso de memória da máquina publisher) e qualquer tópico extra (`--topics TIME SYS NEWS`) |
| Chat | `publisher.py --chat` publica no tópico `CHAT` cada linha digitada no terminal |
| Mensagens multipart `[tópico, JSON]` | O JSON leva nº de sequência, nome do publisher e timestamp |
| Detecção de perdas | O subscriber usa o nº de sequência para avisar mensagens perdidas |
| Atraso de entrega | O subscriber mostra o atraso aproximado de cada mensagem (exige relógios sincronizados — na AWS o *Amazon Time Sync* já cuida disso) |
| Vários publishers | `subscriber.py --hosts ip1 ip2 ...` assina de vários publishers ao mesmo tempo |
| Resumo final | Mensagens recebidas, perdidas e atraso médio por publisher/tópico |
| `--count`, `--interval`, `--timeout` | Controle de quantas mensagens receber/publicar e a cada quanto tempo |
| Compatibilidade | `publisher.py --legacy` envia `TIME` no formato original, para o subscriber original da Fig. 4.22 |

### Fig. 4.23 — Pipeline (PUSH/PULL)

```
 fonte 1 (PUSH) ─┐                         ┌─▶ sink (PULL)  ── relatório
                 ├─▶ workers A,B,C (PULL) ─┤
 fonte 2 (PUSH) ─┘        ▲   (PUSH)       │
                          └──── KILL (PUB/SUB) ◀┘
```

| Funcionalidade | Descrição |
|---|---|
| **Sink** (novo componente) | Coleta os resultados de todos os workers e completa o pipeline fonte → worker → coletor |
| Relatório final | Total de tarefas, tempo, vazão, tarefas por fonte e, por worker: nº de tarefas, % do total, tempo ocupado e soma de *workload* |
| Encerramento automático | As fontes avisam o sink quantas tarefas vão gerar; quando tudo termina, o sink publica `KILL` num canal de controle PUB/SUB e os workers encerram sozinhos (no original eles ficavam em loop infinito) |
| Trabalho real | `--mode cpu` conta os números primos até `workload × 1000` (crivo de Eratóstenes); `--mode sleep` é o comportamento original |
| N fontes / N workers | Qualquer número de fontes (`tasksrc.py 3` usa a porta 4569, etc.); worker aceita `--sources host:porta ...` |
| JSON em vez de `pickle` | `pickle.loads` de dados vindos da rede permite execução de código arbitrário; JSON é seguro e independe da linguagem |
| Parâmetros | `--tasks`, `--interval`, `--min`, `--max` na fonte |

## Como executar

Nos exemplos abaixo, troque os IPs pelos das suas máquinas. Em todos os scripts, `--help`
lista as opções.

### Fig. 4.21 — cliente-servidor

```bash
# máquina A (servidor) — escuta nas portas 4567 e 4568
cd fig421_cliente_servidor
python3 server.py --token segredo
```

```bash
# máquina B (cliente) — comandos únicos
cd fig421_cliente_servidor
python3 client.py --host IP_DO_SERVIDOR --cmd ECHO "Hello world 1"
python3 client.py --host IP_DO_SERVIDOR --port 4568 --cmd CALC "(2+3)*7**2"
python3 client.py --host IP_DO_SERVIDOR --cmd STATS
python3 client.py --host IP_DO_SERVIDOR --bench 1000
```

```bash
# máquina C (cliente) — modo interativo
cd fig421_cliente_servidor
export ZMQ_HOST=IP_DO_SERVIDOR
python3 client.py
```

### Fig. 4.22 — publish-subscribe

```bash
# máquina A (publisher): TIME e SYS a cada 2 s
cd fig422_pub_sub
python3 publisher.py --interval 2
```

```bash
# máquina B (publisher de chat)
cd fig422_pub_sub
python3 publisher.py --chat --topics
```

```bash
# máquina C (subscriber) — recebe de A e B
cd fig422_pub_sub
python3 subscriber.py --hosts IP_A IP_B --topics TIME SYS CHAT --count 0
```

### Fig. 4.23 — pipeline

Defina em **todas** as máquinas do pipeline onde ficam as fontes e o sink:

```bash
export ZMQ_SRC1=IP_FONTE1 ZMQ_SRC2=IP_FONTE2 ZMQ_SINK=IP_SINK
cd fig423_pipeline
```

Depois, cada máquina roda o seu papel (inicie o sink e os workers primeiro):

```bash
python3 sink.py --sources 2                 # máquina do sink
```

```bash
python3 taskwork.py A --mode cpu            # máquina(s) worker
```

```bash
python3 tasksrc.py 1 --tasks 100 --interval 0.1   # máquina fonte 1
```

```bash
python3 tasksrc.py 2 --tasks 100 --interval 0.1   # máquina fonte 2
```

## Implantação na AWS

### 1. Criar as instâncias

1. No console da AWS → **EC2 → Launch instances**.
2. AMI **Ubuntu 24.04** (ou Amazon Linux 2023), tipo **t2.micro/t3.micro** (free tier).
3. Quantidade: 3 a 5 instâncias, **na mesma VPC/subnet** (ex.: `servidor`, `cliente1`, `cliente2`...).
4. Crie/escolha um *key pair* para acesso SSH.

### 2. Security Group (firewall)

Crie um Security Group (ex.: `zmq-lab`) com as regras de **entrada**:

| Tipo | Porta | Origem | Uso |
|---|---|---|---|
| SSH | 22 | Meu IP | acesso às máquinas |
| TCP personalizado | 4567–4570 | o próprio SG `zmq-lab` (ou o CIDR da VPC, ex. `172.31.0.0/16`) | REQ/REP, PUB/SUB e fontes do pipeline |
| TCP personalizado | 5558–5559 | o próprio SG `zmq-lab` | sink do pipeline (resultados e controle) |

Usar o próprio SG como origem libera o tráfego só entre as instâncias do laboratório.
Se quiser conectar do seu computador pelo **IP público**, adicione também as portas com origem "Meu IP".

### 3. Instalar em cada instância

```bash
ssh -i minha-chave.pem ubuntu@IP_PUBLICO
curl -O https://raw.githubusercontent.com/fernandes-emmanuel/zeromq-Modificado/main/aws/setup_ec2.sh
bash setup_ec2.sh https://github.com/fernandes-emmanuel/zeromq-Modificado.git
cd zeromq-Modificado && source venv/bin/activate
```

O script instala `python3-venv`/`git`, clona o repositório, cria o venv, instala o `pyzmq`
e mostra o **IP privado** da máquina (`hostname -I`). Ele também pode ser colado no campo
*User data* ao criar a instância.

### 4. Rodar

Use os comandos da seção [Como executar](#como-executar), usando os **IPs privados**
(`172.31.x.x`) entre instâncias da mesma VPC. Ao testar do seu computador para a AWS,
use o IP público — o servidor continua fazendo `bind` em `*`.

Ao final, pare ou termine as instâncias para não gerar custo.

## Testes realizados e resultados

Os testes entre máquinas diferentes foram feitos com o script
[`docker/teste_multihost.sh`](docker/teste_multihost.sh), que cria uma rede `172.28.0.0/16` e
sobe **cada componente em um container separado, com hostname e IP próprios**
(servidor `172.28.0.10`, clientes `.11`/`.12`, publishers `.20`/`.21`/`.25`, fontes `.30`/`.31`,
sink `.32`, workers `.40`–`.42`). Ele executa tanto o **código original** (apenas com o IP
trocado) quanto as versões estendidas e grava as saídas em [`resultados/`](resultados).

```bash
bash docker/teste_multihost.sh
```

Trechos das saídas obtidas (completas em `resultados/`):

**Fig. 4.21 original** — clientes em `172.28.0.11`/`.12`, servidor em `172.28.0.10`:
```
cliente1 (172.28.0.11) -> porta 4567:
Hello world 1*
cliente2 (172.28.0.12) -> porta 4568:
Hello world 2*
```

**Fig. 4.21 estendida** — log do servidor identificando cada cliente:
```
[21:50:38] servidor servidor (172.28.0.10) escutando nas portas 4567, 4568
[21:50:39] cliente1        ECHO     'Hello world 1' -> Hello world 1*
[21:50:41] cliente1        CALC     '(2+3)*7**2' -> 245
[21:50:42] cliente1        CALC     "__import__('os')" -> CALC: expressao invalida
[21:50:43] cliente2        ECHO     'Hello world 2' -> Hello world 2*
[21:50:43] cliente2        STATS    '' -> {... 'by_client': {'cliente1': 7, 'cliente2': 3}}
[21:50:44] legacy  -> 'Hello world 1'                 <- cliente ORIGINAL
[21:50:45] cliente1        STOP     'errada' -> STOP: senha incorreta
[21:50:46] cliente1        STOP     'segredo' -> servidor encerrando
```
Comparação do tempo de ida e volta (`client.py --bench 1000`):

| Cenário | RTT médio | p95 | Vazão |
|---|---|---|---|
| Cliente e servidor na mesma máquina (`localhost`) | 0,124 ms | 0,144 ms | 8035 req/s |
| Cliente e servidor em máquinas diferentes (`172.28.0.11` → `172.28.0.10`) | 0,333 ms | 0,479 ms | 2999 req/s |

Entre máquinas diferentes, cada requisição passa pela pilha TCP/IP e pela rede, e o RTT
fica cerca de 2,7× maior. Saídas completas em `resultados/fig421_bench_localhost.txt` e
`resultados/fig421_estendido_clientes.txt`.

Benchmark de outro host e comportamento com o servidor fora do ar:
```
benchmark tcp://172.28.0.10:4567: 1000 requisicoes
  media 0.333 ms | mediana 0.320 ms | min 0.179 ms | p95 0.479 ms | max 2.030 ms
  vazao aprox.: 2999 req/s

  [timeout] sem resposta de tcp://172.28.0.10:4567 (tentativa 1/3)
  [timeout] sem resposta de tcp://172.28.0.10:4567 (tentativa 2/3)
  [timeout] sem resposta de tcp://172.28.0.10:4567 (tentativa 3/3)
ERRO: servidor tcp://172.28.0.10:4567 indisponivel
```

**Fig. 4.22 estendida** — um subscriber assinando 2 publishers em máquinas diferentes:
```
assinando topicos: ['SYS', 'NEWS']
[21:51:16] SYS   #1    de pub1         atraso   0.61 ms: {'cpus': 4, 'loadavg': [...], 'mem_used_pct': 4.1}
[21:51:17] SYS   #1    de pub2         atraso   0.39 ms: {...}
[21:51:17] NEWS  #1    de pub2         atraso   0.50 ms: NEWS rodada 1
...
--- resumo ---
pub1         SYS   recebidas=4    perdidas=0   atraso medio=0.49 ms
pub2         NEWS  recebidas=3    perdidas=0   atraso medio=0.46 ms
pub2         SYS   recebidas=3    perdidas=0   atraso medio=0.43 ms
```
O subscriber **original** recebendo do publisher novo (`--legacy`) e o chat entre máquinas:
```
TIME Wed Oct 28 21:51:17 2026
TIME Wed Oct 28 21:51:18 2026
...
[21:51:20] CHAT  #1    de pub3         atraso   0.72 ms: ola de outra maquina!
[21:51:21] CHAT  #2    de pub3         atraso   0.57 ms: ZeroMQ PUB/SUB funcionando
```

**Fig. 4.23 estendida** — 2 fontes, 3 workers (A e B em modo `cpu`, C em modo `sleep`), 1 sink:
```
===== relatorio do pipeline =====
tarefas: 80 em 14.10s (5.7 tarefas/s)
por fonte: 1=40, 2=40
worker                        tarefas        %   ocupado(s)   workload
A@worker1                          27    33.8%         0.01       1199
B@worker2                          27    33.8%         0.02       1505
C@worker3                          26    32.5%        13.00       1299
```
Todos os workers receberam `KILL` do sink e encerraram sozinhos.

## Observações e problemas encontrados

- **`bind` no IP público não funciona na AWS.** A VM só enxerga o IP privado; o IP público é
  um NAT da AWS. Por isso os lados que fazem `bind` usam `*` por padrão (`ZMQ_BIND_HOST`).
- **Security Group** é o motivo mais comum de "o cliente fica travado": o `connect` do ZeroMQ
  é assíncrono e não dá erro se a porta estiver bloqueada — por isso o cliente novo tem timeout.
- **REQ/REP trava sem timeout:** se o servidor cai, o `recv()` do cliente original espera
  para sempre. O padrão *Lazy Pirate* (fechar e recriar o socket REQ) resolve.
- **"Slow joiner" no PUB/SUB:** mensagens publicadas antes de o subscriber terminar de se
  conectar são descartadas. Os números de sequência tornam isso visível; o sink do pipeline
  envia o `KILL` algumas vezes pelo mesmo motivo.
- **PUSH distribui em *round-robin*, sem olhar a carga.** No resultado acima, o worker C
  (lento) recebeu ~⅓ das tarefas e ficou 13 s ocupado, enquanto A e B ficaram quase ociosos:
  o tempo total é ditado pelo worker mais lento. Para balancear pela capacidade de cada
  worker seria preciso trocar PUSH/PULL pelo padrão *load balancing* com ROUTER/REQ, em que o
  worker pede uma tarefa quando fica livre.
- **`pickle` entre máquinas é inseguro** (desserializar dados da rede pode executar código);
  as versões novas usam JSON.
- O atraso medido no PUB/SUB depende de os relógios das máquinas estarem sincronizados (NTP).

# Peladex ⚽

Registre as peladas do seu grupo: monte os times do dia, lance cada partida com placar e
artilheiros, eleja o MVP e acompanhe tabela do dia, ranking, artilharia, evolução do
aproveitamento e com quem cada um joga melhor.

**Stack:** FastAPI + SQLite (backend) · SvelteKit (frontend) · Caddy + Docker Compose (deploy).

## Conceitos

- **Pelada (grupo)** — unidade central. Tem um ou mais **donos** (contas com login).
- **Jogadores** — pessoas da pelada (não são usuários/contas), isolados por grupo.
- **Dia** — uma data, um local opcional, os **times** daquele dia com suas escalações, as
  **partidas** entre eles e os **gols** com artilheiro. O MVP do dia é um campo — a votação
  acontece no grupo e aqui só se registra o eleito.
- **Times são do dia, não da pelada.** BRANCO de uma quinta não é o BRANCO da seguinte.
- **O placar é a fonte da verdade; os artilheiros são atribuição.** Se os dois não fecham,
  o app **avisa** mas deixa salvar — anotar quem fez o gol nem sempre é possível.
- **Gol contra conta para o outro time** e não entra na artilharia de quem fez.
- **Acesso** — slug legível (`/g/minha-pelada`) + visibilidade `public`/`private` +
  `share_token` rotacionável para compartilhar peladas privadas.

### Como o dia é ordenado

No rodízio os times jogam números diferentes de partidas (ontem: 6, 5 e 5). Por isso a
tabela do dia é ordenada por **aproveitamento** — `pontos ÷ pontos possíveis` — e não por
pontos, que premiaria quem calhou de jogar mais. Empate total na liderança deixa o dia
**sem campeão**, em vez de sortear um.

A pontuação é configurável por pelada (padrão 3/1/0) e vale para todo o histórico.

### O que as estatísticas de dupla medem — e o que não medem

Os times são **fixos o dia inteiro**. Para dois jogadores do mesmo time, a "winrate jogando
junto" é literalmente a campanha daquele time naquele dia: **cada dia vale uma observação,
não cada partida**. Por isso:

- `partners` usa o aproveitamento do time **por dia**;
- `opponents` usa o confronto direto entre os dois times **por dia**;
- pares com menos de `min_days` dias juntos **não aparecem** (padrão 3, ajustável na tela).

Com 21 jogadores são 210 duplas possíveis e ~63 observações de dupla por dia. Só depois de
muitas peladas esses números param de ser ruído — o gate é o que impede um "100% em 1 dia"
de encabeçar a lista.

## Rodando em desenvolvimento

**Backend** (porta 8000):
```bash
cd backend
uv venv --python 3.12 .venv          # ou: python3.12 -m venv .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Frontend** (porta 5173, com proxy de `/api` → 8000):
```bash
cd frontend
npm install
npm run dev
```

Acesse http://localhost:5173.

A interface é **bilíngue** (pt-BR/en, botão PT/EN): as strings ficam em
`src/lib/i18n/{pt,en}.js` e são lidas por `t()` — os dois dicionários têm exatamente as
mesmas chaves. O app é uma **SPA client-side**, com uma exceção: as páginas públicas
(`/g/<slug>`, `/g/<slug>/players/<id>` e `/explore`) são **renderizadas no servidor**,
porque são elas que o WhatsApp desdobra e o Google indexa. O SSR renderiza sempre em pt-BR
— o navegador corrige na hidratação — e busca a API pela rede interna
(`PELADEX_API_INTERNAL_URL`).

## Importar do bloco de notas

A tela **Importar texto** (`/groups/<id>/matchdays/import`) aceita a anotação crua, valida
e mostra a tabela do dia **antes** de gravar qualquer coisa. Também aceita um `.txt`.

```
16/09/2026 @ Campo do Ze

BRANCO: golin, galetti, galo, rick, palma, disciplina, mini
VERMELHO: vini, bamma, breno, igor, rod kauer, cesar, beat
AZUL: ney, rod, lusca, pipi, nona, cop, guarino

VERMELHO 0x0 AZUL
BRANCO 0x0 AZUL
BRANCO 1x0 VERMELHO: golin (galetti)
BRANCO 2x0 AZUL: golin, galo (golin)
BRANCO 0x0 VERMELHO
VERMELHO 0x0 AZUL
AZUL 0x1 BRANCO: disciplina
BRANCO 1x1 VERMELHO: golin (mini), vini

MVP: golin
```

Uma linha por coisa, e cada linha se explica sozinha:

| Linha | Significado |
|---|---|
| `16/09/2026 @ Campo do Ze` | abre o dia; o `@ local` é opcional |
| `2026-09-16`, `16/09` | outros formatos de data (sem ano, herda o do dia anterior) |
| `TIME: a, b, c` | escala um time |
| `CASA 2x1 FORA` | uma partida (vale `2-1` e `2 x 1`) |
| `CASA 2x1 FORA: golin, vini` | a mesma partida com os artilheiros |
| `golin (galetti)` | gol do golin, assistência do galetti |
| `golin (gc)` | gol contra — conta para o outro time, e não entra na artilharia dele |
| `golin x2`, `2x golin`, `golin (2)` | dois gols do mesmo jogador |
| `MVP: nome`, `Local: nome`, `Obs: texto` | opcionais |
| `---` | separa um dia do próximo |
| `# comentário` | ignorado |

Os artilheiros também podem ficar na **linha de baixo** da partida, sem os dois-pontos —
que era como a anotação começou. As duas formas convivem.

Três detalhes que valem saber:

- **O parêntese é assistência**, exceto quando o que está dentro é `gc`, `ct`, `contra`
  ou `og` — aí é gol contra. É o único caso especial do formato.
- **`2:1` não vale como placar.** Os dois-pontos já separam a partida dos artilheiros, e
  aceitar os dois deixaria `BRANCO 2:1 VERMELHO: golin` ambíguo. Use `2x1` ou `2-1`.
- Nomes são resolvidos por **correspondência mais longa primeiro**, então `rod` e
  `rod kauer` em times diferentes não se confundem.

O parser **recusa** o texto quando há erro estrutural (time jogando contra si mesmo, time
não escalado, jogador em dois times) e apenas **avisa** quando algo é suspeito mas
plausível: artilheiros que não fecham com o placar, assistência de alguém de outro time,
MVP fora da escalação.

Para backfill em lote existe `backend/scripts/import_text.py`, configurado por constantes
no topo do arquivo (com `APPLY = False` por padrão, que só relata). E
`backend/scripts/seed_demo.py` gera uma temporada inteira de mentira nesse mesmo formato,
para ver o app cheio.

## O que o grupo escolhe anotar

Em **Config** cada pelada liga ou desliga:

- **Anotar quem fez os gols** — desligado, o dia guarda só os placares.
- **Anotar quem deu a assistência** — cada gol pode ter no máximo uma, de alguém do
  **mesmo time**, e gol contra nunca tem. É opcional gol a gol: registrar o gol sem saber
  quem deu o passe é normal.

As duas opções **governam o que a interface mostra**: com artilheiro desligado somem as
colunas de gol e assistência do ranking, os recordes de artilharia, o artilheiro do dia e
o gráfico de gols; com assistência desligada some só a parte dela. O texto importado guarda
o que estiver escrito de qualquer jeito — desligar a opção esconde, não apaga.

A pelada também escolhe um **local padrão**. Ele entra selecionado num dia novo e vale na
importação quando a anotação não traz `@ local` — na prática, quem joga sempre no mesmo
campo nunca mais digita o nome dele.

No formulário, cada gol vira uma etiqueta. **Tocar na etiqueta abre o editor daquele gol**,
onde se escolhe a assistência e se marca gol contra — marcar move o gol de lado no placar
sozinho.

Gols e assistências aparecem com ícone, como em súmula: **bola** para o gol, **chuteira**
para a assistência, **bola vermelha** para o gol contra. São SVG, não emoji, então seguem a
cor do tema e não mudam de desenho entre sistemas.

## Estatísticas

Além da tabela do dia, ranking e artilharia:

- **Aba Jogadores** — o índice de todo mundo, com busca e ordenação, levando à página de
  cada um.
- **Filtro de período** (tudo / 3 / 6 / 12 meses / intervalo) que vale para o ranking, os
  recordes e os gráficos.
- **Últimos 5** — aproveitamento nos cinco últimos dias jogados, e **presença** sobre os
  dias do período.
- **Sequência** de dias como campeão, atual e a maior.
- **Duplas da pelada** — quem rende mais e menos junto, medido por dia e com mínimo de dias.
- **Quem passa pra quem** — o par que mais produz gol, um dando o passe e o outro
  finalizando.
- **Combinações** (`/groups/<id>/analise`) — escolha quem joga junto e, se quiser, contra
  quem; o app acha os dias em que isso aconteceu e compara a campanha com o que se
  esperaria dos jogadores separados.

### Os gráficos

O gráfico de linhas acumuladas troca de **métrica** — aproveitamento, gols ou assistências —
mantendo a mesma legenda. Ele abre com os cinco primeiros, e a legenda tem **Todos** e
**Nenhum**: para comparar duas pessoas, é um clique em Nenhum e dois nomes, em vez de
desligar dezenove.

Do lado do grupo, e não do jogador:

- **Gols por dia** (barras) e **gols por partida** (linha, a média de cada dia).
- **Placares mais comuns**, contando os dois lados juntos — `1x0` e `0x1` são o mesmo
  placar. É o gráfico que mostra o caráter da pelada: na temporada de demonstração, 47%
  das partidas terminam 0x0.
- Os números redondos em cima: gols por partida, gols por dia e assistências por dia.

### A tela do jogador

Cada jogador tem a sua (`/groups/<id>/players/<id>`), e ali a comparação é **com ele
mesmo**, não com a média do grupo:

- **Com X / sem X** — o aproveitamento do seu time nos dias com cada parceiro, contra os
  dias sem ele. Um parceiro que nunca faltou não tem base de comparação, e a tabela diz
  isso em vez de inventar um número.
- **Contra X / sem enfrentar X** — o mesmo para adversários, usando só as partidas contra
  o time dele.
- **Recortes** por local e por time (a cor que pegou no sorteio).
- **Suas combinações** — o explorador de combinações já com ele fixo: é só escolher com
  quem e contra quem.

A diferença importa: comparar "com o fulano" contra a média do grupo mistura o efeito do
parceiro com a fase do próprio jogador. Comparar com os dias sem ele controla isso.

## Migrations (Alembic)

O schema vem **só do Alembic** — não existe `create_all`. No startup o app roda
`alembic upgrade head` sozinho (`app/db.py::run_migrations`), então subir o servidor já
migra o banco. A URL vem **sempre** de `PELADEX_DATABASE_URL`: `alembic.ini` não tem
`sqlalchemy.url`, quem define é `alembic/env.py`.

```bash
cd backend
export PELADEX_DATABASE_URL=sqlite:///./peladex.db
.venv/bin/alembic revision --autogenerate -m "descrição"
.venv/bin/alembic upgrade head
.venv/bin/alembic current
```

`tests/test_migrations.py` falha se os models e as migrations divergirem.

## Testes (backend)

```bash
cd backend
.venv/bin/pytest                     # suíte completa
.venv/bin/pytest -m "not ratelimit"  # sem os que mexem no limiter global
```

Cada execução usa um SQLite temporário migrado pelo Alembic, igual à produção.
`tests/test_queries.py` protege contra N+1: o número de queries de um request não pode
crescer com a quantidade de dias.

## Deploy na VPS (Docker Compose + Cloudflare)

HTTPS é provido pelo **Cloudflare** (proxy laranja, SSL "Flexible"); o origin só fala HTTP
na porta 80. Um **edge proxy** compartilhado (`deploy/edge`) escuta na 80 e roteia por
subdomínio.

```
Cloudflare (HTTPS) → VPS:80 → edge (Caddy http)
    └── peladex.seudominio.com → /api/* → backend:8000 · / → frontend:3000
```

```bash
docker network create web            # uma vez só

git clone <este-repo> peladex && cd peladex
cp .env.example .env                 # ajuste PELADEX_DOMAIN
docker compose up -d --build

cd deploy/edge
cp .env.example .env
docker compose up -d
```

No Cloudflare: registro `peladex` (A/CNAME) **proxied (laranja)**, SSL/TLS = **Flexible**.

O SQLite vive no volume `peladex_data`. O banco roda em **WAL**, então copiar só o
arquivo `.db` pega um estado incompleto — o backup tem que passar pelo `.backup` do
próprio SQLite:

```bash
docker compose exec backend python -c \
  "import sqlite3; s=sqlite3.connect('/data/peladex.db'); d=sqlite3.connect('/data/backup.db'); s.backup(d); d.close()"
docker compose cp backend:/data/backup.db ./backup.db
```

### Variáveis de ambiente (backend)

| Variável | Padrão | Descrição |
|---|---|---|
| `PELADEX_DATABASE_URL` | `sqlite:///./peladex.db` | Caminho do banco |
| `PELADEX_COOKIE_SECURE` | `false` | `true` em produção (HTTPS) |
| `PELADEX_SESSION_TTL_DAYS` | `30` | Validade da sessão |
| `PELADEX_CORS_ORIGINS` | `http://localhost:5173` | Vazio em prod (same-origin) |

### Variáveis de ambiente (frontend)

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `3000` | Porta do servidor Node (adapter-node) |
| `ORIGIN` | — | URL pública; o adapter-node precisa dela para links absolutos |
| `PELADEX_API_INTERNAL_URL` | `http://backend:8000` | Onde o **SSR** busca a API |

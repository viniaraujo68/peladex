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
2026-09-16
Local: Campo do Ze
BRANCO: golin, galetti, galo, rick, palma, disciplina, mini
VERMELHO: vini, bamma, breno, igor, rod kauer, cesar, beat
AZUL: ney, rod, lusca, pipi, nona, cop, guarino
VERMELHO 0x0 AZUL
BRANCO 1x0 VERMELHO
golin
BRANCO 2x0 AZUL
golin galo
MVP: golin
```

Regras do formato:

| Linha | Significado |
|---|---|
| `2026-09-16`, `16/09/2026`, `16/09` | abre um dia (sem ano, herda o do dia anterior do texto) |
| `TIME: a, b, c` | escala um time |
| `CASA 2x1 FORA` | uma partida (vale `2-1`, `2 x 1`, `2:1`) |
| linha seguinte, ou após `:` na própria partida | os artilheiros |
| `(gc)` antes ou depois do nome | gol contra |
| `nome x2`, `2x nome`, `nome (2)` | dois gols do mesmo jogador |
| `MVP: nome`, `Local: nome`, `Obs: …` | opcionais |
| `---` | separa um dia do próximo |
| `# …` | comentário, ignorado |

O parser resolve nomes por **correspondência mais longa primeiro**, então `rod` e
`rod kauer` em times diferentes não se confundem. Ele **recusa** o texto quando há erro
(time jogando contra si mesmo, time não escalado, jogador em dois times) e apenas **avisa**
quando algo é suspeito mas plausível (artilheiros que não fecham com o placar, MVP fora da
escalação).

Para backfill em lote existe `backend/scripts/import_text.py`, configurado por constantes
no topo do arquivo (com `APPLY = False` por padrão, que só relata).

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

O SQLite vive no volume `peladex_data`
(backup = `docker compose cp backend:/data/peladex.db ./backup.db`).

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

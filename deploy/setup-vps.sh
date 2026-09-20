#!/usr/bin/env sh
set -eu

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APPLY="${APPLY:-0}"
DOMAIN="${PELADEX_DOMAIN:-}"

say() { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }
plan() { printf '   [plano] %s\n' "$*"; }
done_() { printf '   [feito] %s\n' "$*"; }
warn() { printf '   [aviso] %s\n' "$*"; }
die() { printf '\nERRO: %s\n' "$*" >&2; exit 1; }

run() {
  if [ "$APPLY" = "1" ]; then
    done_ "$1"
    shift
    "$@"
  else
    plan "$1"
  fi
}

backup() {
  [ -f "$1" ] || return 0
  if [ "$APPLY" = "1" ]; then
    cp "$1" "$1.bak-$(date +%Y%m%d-%H%M%S)"
  fi
}

step "Domínio"
if [ -z "$DOMAIN" ] && [ -f "$APP_DIR/.env" ]; then
  DOMAIN="$(sed -n 's/^PELADEX_DOMAIN=//p' "$APP_DIR/.env" | head -1)"
fi
[ -n "$DOMAIN" ] || die "defina o domínio:  PELADEX_DOMAIN=peladex.seudominio.com sh deploy/setup-vps.sh"
say "   $DOMAIN"

step "Rede docker"
if docker network inspect web >/dev/null 2>&1; then
  say "   rede 'web' já existe"
else
  run "docker network create web" docker network create web
fi

step "Procurando o proxy da porta 80"
EDGE_ID="$(docker ps --format '{{.ID}} {{.Ports}}' | grep -E ':80->' | awk '{print $1}' | head -1 || true)"
if [ -z "$EDGE_ID" ]; then
  say "   nenhum container publicando a porta 80"
  EDGE_DIR=""
  CADDYFILE=""
else
  EDGE_NAME="$(docker inspect "$EDGE_ID" --format '{{.Name}}' | sed 's|^/||')"
  EDGE_IMAGE="$(docker inspect "$EDGE_ID" --format '{{.Config.Image}}')"
  EDGE_DIR="$(docker inspect "$EDGE_ID" --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}')"
  CADDYFILE="$(docker inspect "$EDGE_ID" --format '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}')"
  say "   container: $EDGE_NAME ($EDGE_IMAGE)"
  say "   pasta:     ${EDGE_DIR:-desconhecida}"
  say "   Caddyfile: ${CADDYFILE:-nenhum montado}"
  case "$EDGE_IMAGE" in
    *caddy*) : ;;
    *) die "o proxy não é Caddy ($EDGE_IMAGE). Pare aqui e me mostre a config dele." ;;
  esac
  [ -n "$CADDYFILE" ] || die "o Caddy não tem um Caddyfile montado do host; não dá para editar de fora."
  [ -f "$CADDYFILE" ] || die "Caddyfile apontado em $CADDYFILE não existe no host."
fi

step "Subindo o Peladex"
if [ ! -f "$APP_DIR/.env" ]; then
  run "criar $APP_DIR/.env com PELADEX_DOMAIN=$DOMAIN" sh -c "printf 'PELADEX_DOMAIN=%s\n' '$DOMAIN' > '$APP_DIR/.env'"
elif ! grep -q '^PELADEX_DOMAIN=' "$APP_DIR/.env"; then
  run "acrescentar PELADEX_DOMAIN a $APP_DIR/.env" sh -c "printf 'PELADEX_DOMAIN=%s\n' '$DOMAIN' >> '$APP_DIR/.env'"
else
  say "   .env do app já tem PELADEX_DOMAIN"
fi
run "docker compose up -d --build (em $APP_DIR)" sh -c "cd '$APP_DIR' && docker compose up -d --build"

if [ -z "$CADDYFILE" ]; then
  step "Proxy"
  warn "sem proxy na porta 80. O Peladex subiu, mas nada o publica ainda."
  warn "Se as outras apps usam Cloudflare Tunnel ou portas diretas, me diga qual é o caso."
  exit 0
fi

step "Ensinando o proxy sobre $DOMAIN"
SITES_DIR=""
if grep -q 'import .*sites/\*' "$CADDYFILE" 2>/dev/null; then
  SITES_DIR="$(dirname "$CADDYFILE")/sites"
  say "   o edge usa import de sites/"
fi

if grep -q 'PELADEX_DOMAIN' "$CADDYFILE" 2>/dev/null || \
   { [ -n "$SITES_DIR" ] && [ -f "$SITES_DIR/peladex.caddy" ]; }; then
  say "   o proxy já conhece o Peladex"
else
  if [ -n "$SITES_DIR" ]; then
    run "copiar deploy/peladex.caddy para $SITES_DIR/" sh -c "mkdir -p '$SITES_DIR' && cp '$APP_DIR/deploy/peladex.caddy' '$SITES_DIR/peladex.caddy'"
  else
    backup "$CADDYFILE"
    run "acrescentar o bloco do Peladex a $CADDYFILE (backup .bak-*)" sh -c "printf '\n' >> '$CADDYFILE' && cat '$APP_DIR/deploy/peladex.caddy' >> '$CADDYFILE'"
  fi
fi

EDGE_ENV="$EDGE_DIR/.env"
if [ -n "$EDGE_DIR" ] && [ -d "$EDGE_DIR" ]; then
  if [ -f "$EDGE_ENV" ] && grep -q '^PELADEX_DOMAIN=' "$EDGE_ENV"; then
    say "   .env do edge já tem PELADEX_DOMAIN"
  else
    backup "$EDGE_ENV"
    run "acrescentar PELADEX_DOMAIN a $EDGE_ENV" sh -c "printf 'PELADEX_DOMAIN=%s\n' '$DOMAIN' >> '$EDGE_ENV'"
  fi

  EDGE_COMPOSE=""
  for f in "$EDGE_DIR/docker-compose.yml" "$EDGE_DIR/docker-compose.yaml" "$EDGE_DIR/compose.yml" "$EDGE_DIR/compose.yaml"; do
    [ -f "$f" ] && EDGE_COMPOSE="$f" && break
  done
  if [ -z "$EDGE_COMPOSE" ]; then
    warn "não achei o compose do edge em $EDGE_DIR; passe PELADEX_DOMAIN para o container na mão."
  elif grep -q 'env_file' "$EDGE_COMPOSE"; then
    say "   o compose do edge usa env_file: nada a mudar"
  elif grep -q 'PELADEX_DOMAIN' "$EDGE_COMPOSE"; then
    say "   o compose do edge já passa PELADEX_DOMAIN"
  else
    backup "$EDGE_COMPOSE"
    run "trocar 'environment:' por 'env_file: .env' em $EDGE_COMPOSE (backup .bak-*)" \
      sed -i 's/^\( *\)environment:.*/\1env_file: .env/' "$EDGE_COMPOSE"
    warn "se o edge tinha outras variáveis no environment:, confira que todas estão no .env dele"
  fi

  run "recriar o edge e recarregar a config" sh -c "cd '$EDGE_DIR' && docker compose up -d && sleep 2 && docker compose exec -T \$(docker compose config --services | head -1) caddy reload --config /etc/caddy/Caddyfile"
else
  warn "não descobri a pasta do edge; reinicie-o na mão depois de conferir o Caddyfile."
fi

step "Conferindo"
if [ "$APPLY" = "1" ]; then
  sleep 3
  for h in "$DOMAIN"; do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 -H "Host: $h" http://127.0.0.1/ || echo 000)"
    api="$(curl -s --max-time 8 -H "Host: $h" http://127.0.0.1/api/health || echo falhou)"
    say "   $h  ->  HTTP $code   /api/health: $api"
  done
  say ""
  say "Se deu 200 e {\"status\":\"ok\"}, acesse https://$DOMAIN e crie sua conta."
else
  say ""
  say "Isso foi só o plano. Para executar:"
  say "   APPLY=1 sh deploy/setup-vps.sh"
fi

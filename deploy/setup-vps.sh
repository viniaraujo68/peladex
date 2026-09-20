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
BLOCK="$(mktemp)"
sed "s/{\$PELADEX_DOMAIN}/$DOMAIN/" "$APP_DIR/deploy/peladex.caddy" > "$BLOCK"

SITES_DIR=""
if grep -q 'import .*sites/\*' "$CADDYFILE" 2>/dev/null; then
  SITES_DIR="$(dirname "$CADDYFILE")/sites"
  say "   o edge usa import de sites/"
fi

if grep -q "$DOMAIN" "$CADDYFILE" 2>/dev/null || \
   { [ -n "$SITES_DIR" ] && [ -f "$SITES_DIR/peladex.caddy" ]; }; then
  say "   o proxy já conhece $DOMAIN"
else
  if [ -n "$SITES_DIR" ]; then
    run "criar $SITES_DIR/peladex.caddy" sh -c "mkdir -p '$SITES_DIR' && cp '$BLOCK' '$SITES_DIR/peladex.caddy'"
  else
    backup "$CADDYFILE"
    run "acrescentar o bloco do Peladex a $CADDYFILE (backup .bak-*)" \
      sh -c "printf '\n' >> '$CADDYFILE' && cat '$BLOCK' >> '$CADDYFILE'"
  fi
fi
rm -f "$BLOCK"

step "Recarregando o proxy"
if [ "$APPLY" = "1" ]; then
  if ! docker exec "$EDGE_ID" caddy validate --config /etc/caddy/Caddyfile >/dev/null 2>&1; then
    docker exec "$EDGE_ID" caddy validate --config /etc/caddy/Caddyfile || true
    die "a config do Caddy ficou inválida. O proxy continua rodando a config antiga (rastro e pokerdex seguem no ar). Desfaça com o arquivo .bak-* e me mostre o erro acima."
  fi
  done_ "config válida, recarregando (sem reiniciar o container)"
  docker exec "$EDGE_ID" caddy reload --config /etc/caddy/Caddyfile
else
  plan "validar a config e dar 'caddy reload' no $EDGE_NAME (sem reiniciar)"
fi

step "Conferindo"
if [ "$APPLY" = "1" ]; then
  sleep 3
  HOSTS="$(cat "$CADDYFILE" ${SITES_DIR:+$SITES_DIR/*.caddy} 2>/dev/null \
    | sed -n 's/^[[:space:]]*http:\/\/\([^ ,]*\).*/\1/p' | sed 's/{$//' | sort -u)"
  for h in $HOSTS; do
    case "$h" in
      '{$'*)
        var="$(printf '%s' "$h" | sed 's/^{\$//; s/}$//')"
        h="$(docker exec "$EDGE_ID" printenv "$var" 2>/dev/null || echo '')"
        [ -n "$h" ] || continue
        ;;
    esac
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 -H "Host: $h" http://127.0.0.1/ || echo 000)"
    if [ "$h" = "$DOMAIN" ]; then
      api="$(curl -s --max-time 8 -H "Host: $h" http://127.0.0.1/api/health || echo falhou)"
      say "   $h  ->  HTTP $code   /api/health: $api"
    else
      say "   $h  ->  HTTP $code"
    fi
  done
  say ""
  say "Todos os sites acima devem responder 200/3xx."
  say "Se o $DOMAIN deu 200 e {\"status\":\"ok\"}, acesse https://$DOMAIN e crie sua conta."
else
  say ""
  say "Isso foi so o plano. Para executar:"
  say "   APPLY=1 sh deploy/setup-vps.sh"
fi

#!/usr/bin/env bash
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="backend"
DB_PATH="/data/peladex.db"
STAGE_PATH="/data/backup-stage.db"
BACKUP_DIR="$HOME/backups/peladex"
KEEP_DAYS=45

stamp="$(date +%Y%m%d-%H%M%S)"
target="$BACKUP_DIR/peladex-$stamp.db"

mkdir -p "$BACKUP_DIR"
cd "$COMPOSE_DIR"

docker compose exec -T "$SERVICE" python -c "
import sqlite3, sys
source = sqlite3.connect('$DB_PATH')
staged = sqlite3.connect('$STAGE_PATH')
source.backup(staged)
source.close()
result = staged.execute('PRAGMA integrity_check').fetchone()[0]
matchdays = staged.execute('select count(*) from matchday').fetchone()[0]
staged.close()
if result != 'ok':
    sys.exit(f'integrity_check falhou: {result}')
print(f'staged ok, {matchdays} dia(s)')
"

docker compose cp "$SERVICE:$STAGE_PATH" "$target"
docker compose exec -T "$SERVICE" rm -f "$STAGE_PATH"
gzip -f "$target"
gzip -t "$target.gz"

find "$BACKUP_DIR" -name 'peladex-*.db.gz' -mtime "+$KEEP_DAYS" -delete

echo "ok: $target.gz ($(du -h "$target.gz" | cut -f1)), $(ls -1 "$BACKUP_DIR" | wc -l) arquivo(s) guardado(s)"

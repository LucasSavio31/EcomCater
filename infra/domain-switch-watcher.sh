#!/bin/bash
# Aplica a troca de domínio pedida pela API (arquivo-gatilho, ver
# api/app/modules/domains/service.py `_request_domain_switch`).
#
# A API roda dentro de um container, sem acesso a `.env`/Docker do host --
# ela só ESCREVE este arquivo numa pasta compartilhada (bind mount). Este
# script roda FORA do container, direto no host (via systemd timer, mesmo
# esquema do auto-deploy.sh), lê o pedido e aplica sozinho: troca as
# variáveis do site no `.env` e rebuilda api/frontend/admin.
#
# Dois modos:
#   mode=domain -> usa o domínio (HTTPS, portas só em 127.0.0.1 -- o
#                  aaPanel/LiteSpeed é quem fica público)
#   mode=ip     -> sem domínio nenhum ativo, volta pro acesso direto por
#                  IP:PORTA (HTTP puro, portas em 0.0.0.0) -- pra nunca
#                  ficar sem conseguir entrar na loja/admin. O IP público é
#                  detectado sozinho, sem configuração manual.
set -euo pipefail

COMPOSE_DIR="/opt/cater"
TRIGGER_FILE="$COMPOSE_DIR/.data/triggers/domain-switch.json"
ENV_FILE="$COMPOSE_DIR/.env"
LOG_FILE="$COMPOSE_DIR/domain-switch.log"

[ -f "$TRIGGER_FILE" ] || exit 0

log() { echo "[$(date -Is)] $*" >>"$LOG_FILE"; }

MODE=$(jq -r '.mode // empty' "$TRIGGER_FILE" 2>/dev/null || true)
if [ -z "$MODE" ]; then
  log "trigger sem 'mode' válido -- descartando"
  rm -f "$TRIGGER_FILE"
  exit 0
fi

set_env() {
  # set_env CHAVE VALOR -- atualiza a linha no .env, ou cria se não existir
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s#^${key}=.*#${key}=${val}#" "$ENV_FILE"
  else
    echo "${key}=${val}" >>"$ENV_FILE"
  fi
}

detect_public_ip() {
  # 1ª tentativa: IP de saída da própria interface (sem depender de
  # serviço externo). 2ª: serviço externo, só se a 1ª falhar.
  local ip
  ip=$(ip route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')
  if [ -z "$ip" ]; then
    ip=$(curl -fsS --max-time 5 https://api.ipify.org || true)
  fi
  echo "$ip"
}

cp "$ENV_FILE" "$ENV_FILE.bak-$(date +%s)"
log "processando troca: mode=$MODE"

if [ "$MODE" = "ip" ]; then
  PUBLIC_IP=$(detect_public_ip)
  if [ -z "$PUBLIC_IP" ]; then
    log "ERRO: não consegui detectar o IP público -- mantendo o gatilho pra tentar de novo"
    exit 1
  fi
  log "modo IP -- usando $PUBLIC_IP"
  set_env PUBLIC_BIND_ADDR "0.0.0.0"
  set_env SITE_URL "http://$PUBLIC_IP:3000"
  set_env PUBLIC_API_URL "http://$PUBLIC_IP:8000"
  set_env ADMIN_URL "http://$PUBLIC_IP:3001/administracao"
  set_env NEXT_PUBLIC_SITE_URL "http://$PUBLIC_IP:3000"
  set_env NEXT_PUBLIC_API_URL "http://$PUBLIC_IP:8000"
  set_env NEXT_PUBLIC_ADMIN_API_URL "http://$PUBLIC_IP:8000"
  set_env CORS_ORIGINS "http://$PUBLIC_IP:3000,http://$PUBLIC_IP:3001"
elif [ "$MODE" = "domain" ]; then
  HOSTNAME_=$(jq -r '.hostname' "$TRIGGER_FILE")
  ADMIN_HOST=$(jq -r '.admin_hostname' "$TRIGGER_FILE")
  API_HOST=$(jq -r '.api_hostname' "$TRIGGER_FILE")
  log "modo domínio -- $HOSTNAME_"
  set_env PUBLIC_BIND_ADDR "127.0.0.1"
  set_env SITE_URL "https://$HOSTNAME_"
  set_env PUBLIC_API_URL "https://$API_HOST"
  set_env ADMIN_URL "https://$ADMIN_HOST/administracao"
  set_env NEXT_PUBLIC_SITE_URL "https://$HOSTNAME_"
  set_env NEXT_PUBLIC_API_URL "https://$API_HOST"
  set_env NEXT_PUBLIC_ADMIN_API_URL "https://$API_HOST"
  set_env CORS_ORIGINS "https://$HOSTNAME_,https://$ADMIN_HOST"
else
  log "mode desconhecido: '$MODE' -- descartando"
  rm -f "$TRIGGER_FILE"
  exit 0
fi

cd "$COMPOSE_DIR"
if docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --force-recreate api frontend admin >>"$LOG_FILE" 2>&1; then
  rm -f "$TRIGGER_FILE"
  log "troca concluída com sucesso"
else
  log "ERRO: rebuild falhou -- mantendo o gatilho pra tentar de novo no próximo tick"
  exit 1
fi

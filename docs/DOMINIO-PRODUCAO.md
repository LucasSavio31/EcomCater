# Checklist — apontar o domínio real em produção

> Hoje a produção roda **direto no IP da VPS** (`167.86.92.107`), com HTTPS de
> certificado autoassinado (por isso o navegador mostra aviso de segurança).
> Este checklist é pra quando o domínio estiver pronto pra apontar de verdade.
> Nada aqui foi feito ainda — é o roteiro pra seguir nesse dia.

## 0. Antes de começar
- [ ] DNS do domínio (e do subdomínio do admin, se for usar um) apontando pro
      IP da VPS (`167.86.92.107`) — registro `A`. Dá pra confirmar com
      `dig +short seudominio.com`.
- [ ] Decidir a topologia: loja na raiz do domínio
      (`https://seudominio.com`) + admin num subdomínio
      (`https://admin.seudominio.com`) é o padrão mais simples de fazer com
      certificado — evita depender de porta não-443 pra admin/api.

## 1. Certificado TLS de verdade (Let's Encrypt)
O autoassinado atual (`/opt/cater/certs`) precisa ser trocado por um emitido
de verdade. Mais simples: `certbot` (modo standalone, ocupando a porta 80
brevemente) direto na VPS, fora do Docker:
- [ ] `apt install certbot` (ou snap) na VPS.
- [ ] Parar o container `cater-proxy` um instante (ele ocupa as portas
      3000/3001/8000, não a 80 — só precisa garantir que nada mais escute 80).
- [ ] `certbot certonly --standalone -d seudominio.com -d admin.seudominio.com`
- [ ] Copiar `fullchain.pem`/`privkey.pem` gerados pra
      `/opt/cater/certs/cert.pem` e `/opt/cater/certs/key.pem` (os nomes que o
      `docker-compose.prod.yml` já espera).
- [ ] Configurar renovação automática (`certbot renew` via cron/systemd timer)
      — certificado Let's Encrypt expira em 90 dias.

## 2. Atualizar `infra/proxy/nginx.conf`
Hoje cada serviço escuta uma porta HTTPS própria (3000/3001/8000) porque não
havia domínio pra rotear por `server_name`. Com domínio, o padrão é:
- [ ] Trocar os 3 blocos `server { listen 3000/3001/8000 ssl; }` por blocos
      `listen 443 ssl;` com `server_name` diferente cada um
      (`seudominio.com` → frontend, `admin.seudominio.com` → admin,
      `api.seudominio.com` → api).
- [ ] Adicionar um `server { listen 80; return 301 https://$host$request_uri; }`
      pra redirecionar HTTP → HTTPS (hoje isso só existe via `error_page 497`).
- [ ] Rodar `docker run --rm -v .../nginx.conf:/etc/nginx/nginx.conf:ro -v .../certs:/certs:ro nginx:1.27-alpine nginx -t`
      pra validar a sintaxe **antes** de aplicar (mesmo truque usado nesta
      sessão) — evita derrubar loja/admin/api por um erro de digitação.

## 3. Variáveis de ambiente (`.env` na VPS, `/opt/cater/.env`)
Trocar de IP pra domínio nestas chaves e rodar o deploy de novo (o `frontend`/
`admin` precisam **rebuildar**, não só reiniciar — `NEXT_PUBLIC_*` é
embutido no build):
- [ ] `CORS_ORIGINS=https://seudominio.com,https://admin.seudominio.com`
- [ ] `SITE_URL=https://seudominio.com`
- [ ] `NEXT_PUBLIC_API_URL=https://api.seudominio.com`
- [ ] `NEXT_PUBLIC_SITE_URL=https://seudominio.com`
- [ ] `NEXT_PUBLIC_ADMIN_API_URL=https://api.seudominio.com`
- [ ] Rodar `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` (ou só `bash auto-deploy.sh` depois de commitar/pushar o `.env`
      — **atenção**: `.env` não é versionado, essa parte é manual na VPS).

## 4. Content-Security-Policy (deixada de fora de propósito na auditoria)
A auditoria de segurança desta sessão adicionou `X-Frame-Options`,
`X-Content-Type-Options`, `Referrer-Policy` e HSTS, mas **não** uma CSP —
a loja usa GTM/GA4/Meta Pixel com scripts inline, e uma CSP errada quebra
isso silenciosamente (o navegador só bloqueia, sem erro no servidor).
- [ ] Com o domínio definitivo, montar uma CSP liberando: `self`,
      `https://www.googletagmanager.com`, `https://www.google-analytics.com`
      (+ `*.analytics.google.com`), `https://connect.facebook.net`,
      `https://www.facebook.com`, e o próprio `https://api.seudominio.com`
      (imagens de produto).
- [ ] Depois de aplicar, **repetir o teste de dataLayer** (script Playwright
      usado nesta sessão: home → produto → carrinho → checkout) e confirmar
      que `gtm.js`/`view_item`/`add_to_cart`/`purchase` ainda disparam.

## 5. Pagamento — sair do modo "fake"
Produção hoje usa o gateway **`fake`** (aprova na hora, sem gateway real —
confirmado funcionando nesta sessão, mas **nenhum pagamento é cobrado de
verdade**). Antes de aceitar cliente real:
- [ ] Admin → Pagamento: trocar `active_provider` de `fake` pra `appmax`.
- [ ] Preencher `appmax_access_token` (produção, não sandbox).
- [ ] Preencher `appmax_webhook_secret` — **obrigatório**: depois da correção
      desta auditoria, o webhook da Appmax **recusa tudo** (fail-closed) se
      esse segredo não estiver configurado. Sem ele, nenhum pagamento real
      confirma sozinho.
- [ ] Testar 1 compra real de baixo valor de ponta a ponta antes de divulgar
      a loja.

## 6. Frete — confirmar Melhor Envio em produção (não sandbox)
- [ ] Admin → Frete: confirmar `melhor_envio_sandbox = false` e que o token
      é o de produção (o teste desta sessão já bateu em
      `www.melhorenvio.com.br`, não `sandbox.`, então isso já parece OK —
      só reconfirmar antes do lançamento).
- [ ] Configurar `webhook_token` (mesma lógica do item 5: sem ele, o webhook
      de rastreio agora recusa tudo).

## 7. Segurança — itens que dependem de você
- [ ] Ativar MFA (2FA) na conta admin — Admin → Minha conta. Já existe, só
      não está ligado.
- [ ] Trocar a senha root da VPS (foi compartilhada em texto puro no chat
      desta sessão pra eu configurar acesso por chave SSH).

## 8. Depois de tudo no ar
- [ ] `curl -I https://seudominio.com` sem aviso de certificado.
- [ ] Loja, admin e checkout completo (endereço → frete → pagamento →
      obrigado) funcionando no domínio novo.
- [ ] `/docs` e `/openapi.json` continuam bloqueados
      (`curl -o /dev/null -w '%{http_code}' https://api.seudominio.com/docs` → `404`).
- [ ] Cabeçalhos de segurança presentes
      (`curl -I https://seudominio.com | grep -i strict-transport`).

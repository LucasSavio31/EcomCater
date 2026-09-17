# Domínio em produção

> Isto costumava ser um roteiro manual (DNS → certbot → editar `nginx.conf` →
> trocar `.env` → rebuild). Agora é automático: **Admin → Infraestrutura →
> Domínio**. Este arquivo documenta o que ainda precisa ser feito à mão (fora
> do admin) e o que sobrou de checklist manual pra depois de o domínio estar
> no ar.

## Como funciona

A VPS já tem **aaPanel + OpenLiteSpeed** instalados (era só o painel padrão,
sem nenhum site configurado). Ele passa a ser o único ponto de entrada
público (portas 80/443): termina TLS com certificado real (Let's Encrypt) por
domínio e faz proxy reverso pro `cater-proxy` (nginx no Docker), que continua
rodando — só que agora em HTTP puro, só em `127.0.0.1` (nunca exposto direto)
— e continua fazendo o que já fazia bem: gzip, cache de `/api/products`
etc., headers de segurança, streaming do SSR.

Ao cadastrar um domínio em **Infraestrutura → Domínio** e clicar em Salvar, a
API:
1. (se a Cloudflare estiver configurada) garante a zona do domínio lá —
   cria se não existir — e mostra os **nameservers** pra você trocar no
   registrador do domínio (onde ele foi comprado). Fica em
   *"Aguardando nameservers"* até propagar; checamos sozinhos a cada 5 min e
   paramos de checar assim que confirmar.
2. Uma vez o DNS resolvendo, cria os registros A/CNAME automaticamente (ou
   mostra as instruções, se você preferir configurar na mão / usar outro
   provedor de DNS).
3. Cria o vhost com proxy reverso no aaPanel pra `<domínio>`,
   `admin.<domínio>` e `api.<domínio>` (cada um apontando pro `cater-proxy`
   internamente).
4. Emite o certificado SSL (Let's Encrypt) pelos três, via API do aaPanel.

Dá pra trocar de domínio depois — mesma tela, mesmo fluxo. O antigo vhost/SSL
não é apagado automaticamente ao remover um domínio da lista (fica só como
"não rastreado mais aqui" — evita apagar algo em uso por engano).

## Pré-requisitos manuais (uma vez, fora do admin)

- [ ] **aaPanel**: painel da VPS → Configurações → API → habilitar e copiar
      a chave. Colar em Infraestrutura → Domínio → Credenciais junto com a
      URL do painel.
- [ ] **Cloudflare** (opcional, mas recomendado): criar um **API Token**
      (não a Global Key) com permissão só `Zone → DNS → Edit`, restrito à
      zona do domínio. Sem isso, o DNS fica manual — a tela sempre mostra as
      instruções de qualquer forma.
- [ ] Testar as duas antes de cadastrar um domínio: botão "Testar conexão"
      na mesma tela.

## O que ainda é manual depois do domínio estar ativo

### Variáveis de ambiente (`.env` na VPS, `/opt/cater/.env`)
`NEXT_PUBLIC_*` é embutido no build do Next — trocar de IP pra domínio exige
rebuild do `frontend`/`admin`, não só reiniciar:
- [ ] `CORS_ORIGINS=https://seudominio.com,https://admin.seudominio.com`
- [ ] `SITE_URL=https://seudominio.com`
- [ ] `NEXT_PUBLIC_API_URL=https://api.seudominio.com`
- [ ] `NEXT_PUBLIC_SITE_URL=https://seudominio.com`
- [ ] `NEXT_PUBLIC_ADMIN_API_URL=https://api.seudominio.com`
- [ ] Rodar `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` (ou `bash auto-deploy.sh` depois de commitar/pushar — o `.env` em si não é versionado, essa parte é manual na VPS).

### Content-Security-Policy (deixada de fora de propósito)
A loja usa GTM/GA4/Meta Pixel com scripts inline, e uma CSP errada quebra
isso silenciosamente. Com o domínio definitivo:
- [ ] Montar uma CSP liberando: `self`, `https://www.googletagmanager.com`,
      `https://www.google-analytics.com` (+ `*.analytics.google.com`),
      `https://connect.facebook.net`, `https://www.facebook.com`, e o
      próprio `https://api.seudominio.com` (imagens de produto).
- [ ] Repetir o teste de dataLayer (home → produto → carrinho → checkout) e
      confirmar que `gtm.js`/`view_item`/`add_to_cart`/`purchase` disparam.

### Pagamento — sair do modo "fake"
- [ ] Admin → Pagamento: trocar `active_provider` de `fake` pra `appmax`,
      preencher `appmax_access_token` (produção) e `appmax_webhook_secret`
      (obrigatório — sem ele o webhook recusa tudo).
- [ ] Testar 1 compra real de baixo valor de ponta a ponta.

### Frete — confirmar Melhor Envio em produção
- [ ] Admin → Frete: `melhor_envio_sandbox = false`, token de produção,
      `webhook_token` preenchido (mesma lógica — sem ele o webhook recusa
      tudo).

### Segurança
- [ ] Ativar MFA (2FA) na conta admin — já existe, só não está ligado.
- [ ] Trocar a senha root da VPS se ela já foi compartilhada em texto puro
      em algum momento.

### Checklist final
- [ ] `curl -I https://seudominio.com` sem aviso de certificado.
- [ ] Loja, admin e checkout completo funcionando no domínio novo.
- [ ] `/docs` e `/openapi.json` continuam bloqueados
      (`curl -o /dev/null -w '%{http_code}' https://api.seudominio.com/docs` → `404`).
- [ ] Cabeçalhos de segurança presentes
      (`curl -I https://seudominio.com | grep -i strict-transport`).

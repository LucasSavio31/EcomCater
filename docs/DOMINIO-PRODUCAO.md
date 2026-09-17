# Domínio em produção

> Isto costumava ser um roteiro manual (DNS → certbot → editar `nginx.conf` →
> trocar `.env` → rebuild). Agora é automático: **Admin → Infraestrutura →
> Domínio**. Este arquivo documenta como funciona de verdade (depois de ter
> sido testado ponta a ponta em produção, incluindo os problemas reais que
> apareceram — não é mais só a intenção de design) e o que ainda precisa ser
> feito à mão.

## Como funciona (arquitetura atual)

A VPS tem **aaPanel + OpenLiteSpeed** instalados, e ele é o **único** ponto de
entrada público (portas 80/443) — termina TLS com certificado real (Let's
Encrypt) por domínio e faz proxy reverso **direto pros containers**:

```
Internet → Cloudflare (proxy laranja, opcional) → LiteSpeed (80/443, SSL)
         → 127.0.0.1:3000 (cater-front) / :3001 (cater-admin) / :8000 (cater-api)
```

**Não existe mais nginx no meio** (o antigo container `cater-proxy` foi
removido) — cada app (`api`, `frontend`, `admin`) publica sua própria porta
direto em `127.0.0.1` no `docker-compose.prod.yml`, e o LiteSpeed fala com
elas diretamente. Motivo: o nginx intermediário começou a devolver
`Connection reset by peer` de forma não-diagnosticada depois da migração pra
domínio, e a solução mais simples/robusta foi tirá-lo do caminho — LiteSpeed
já faz gzip/TLS/roteamento por conta própria.

Ao cadastrar um domínio em **Infraestrutura → Domínio** e clicar em Salvar:

1. **Zona Cloudflare** (se configurada): garante que a zona existe — só
   **encontra**, não cria, a não ser que o token tenha permissão de conta
   pra isso (ver seção de credenciais). Mostra os **nameservers** pra trocar
   no registrador. Fica em *"Aguardando nameservers"* até a zona confirmar
   `active`; checamos sozinhos a cada 5 min e paramos assim que confirmar
   (só reativa se o domínio for removido e recadastrado).
2. **Registros DNS**: A (raiz → IP da VPS) + CNAME (`admin.`/`api.` → raiz),
   criados assim que a zona existe (não precisa esperar `active` — a
   Cloudflare aceita registros numa zona `pending`, só não ficam públicos
   até propagar).
3. **Site + proxy reverso no aaPanel**, pros três hosts (raiz, `admin.`,
   `api.`), apontando pra `127.0.0.1:3000/3001/8000`.
4. **SSL** (Let's Encrypt) pelos três, via aaPanel.

Falha em SSL **não** derruba o domínio pra `failed` — nesse ponto o site já
responde por HTTP, então fica `active` com `ssl_status=error` e uma rotina
de fundo tenta de novo sozinha.

## Credenciais — pré-requisitos manuais

- [ ] **aaPanel**: painel da VPS → Configurações → API → habilitar e copiar
      a chave. Colar em Infraestrutura → Domínio → Credenciais junto com a
      URL do painel (a porta do painel é a que aparece na URL de acesso —
      **não** é sempre 888/8888, cada instalação tem a sua).
- [ ] **Cloudflare** — criar um **API Token** (não a Global Key). Duas
      permissões, cada uma com seu próprio escopo:
  - `Zone → DNS → Edit`, escopado a **"All zones from an account"** (não dá
    pra restringir a uma zona específica se o domínio ainda não existe na
    conta — o seletor da Cloudflare nem mostra a opção).
  - `Account → Zone → Edit` + **Account Resources: Include → sua conta** —
    só é necessário se você quiser que a automação **crie a zona do zero**
    pra um domínio que nunca esteve na Cloudflare. **Isso não funcionou de
    forma confiável em teste real** (a Cloudflare recusa `zone.create` por
    token mesmo com a permissão marcada, dependendo do tipo de conta) — o
    plano B que sempre funciona: adicionar o site manualmente em
    "Add a site" no dashboard da Cloudflare (30 segundos, zona nova). Depois
    disso, com só a permissão de DNS, a automação segue 100% sozinha dali
    pra frente (DNS, proxy, SSL).
  - `Zone → Cache Rules → Edit` — só necessário se for usar a seção de
    **Cache** (ver abaixo).
- [ ] Testar tudo antes de cadastrar um domínio: botão "Testar conexão" na
      mesma tela.

## Cache (Cloudflare Cache Rules)

Depois que um domínio confirma o DNS, a tela mostra checkboxes por tipo de
página (Início, Categorias, Produto, Páginas institucionais, Busca) — marcar
aplica regras de cache agressivo na Cloudflare pra esses caminhos via API
(`PUT /zones/{zona}/rulesets/phases/http_request_cache_settings/entrypoint`).
**Carrinho, Checkout, Minha conta, Favoritos e recuperação de senha nunca
são cacheados** — é regra fixa no código, não uma opção da tela (protege
contra vazamento de sessão/carrinho de um visitante pra outro). `admin.` e
`api.` também nunca entram nesse cache.

## Depois que o domínio está `active` — troca de `.env` (manual)

`NEXT_PUBLIC_*` é embutido no **build** do Next — trocar de IP pra domínio
exige rebuild do `frontend`/`admin`, não só reiniciar. **Atenção**, tem uma
variável fácil de esquecer que não é `NEXT_PUBLIC_*` mas também define URL
pública:

- [ ] `CORS_ORIGINS=https://seudominio.com,https://admin.seudominio.com`
- [ ] `SITE_URL=https://seudominio.com`
- [ ] `PUBLIC_API_URL=https://api.seudominio.com`
- [ ] **`MEDIA_BASE_URL=https://api.seudominio.com/media`** — usada pela API
      pra montar a URL de toda imagem (produto, banner, logo). Separada de
      `PUBLIC_API_URL` porque foi criada antes de existir domínio — fácil de
      esquecer e o sintoma é sutil (banner/logo aparecem, produtos não, ou
      vice-versa, dependendo do que já regenerou cache).
- [ ] `NEXT_PUBLIC_API_URL=https://api.seudominio.com`
- [ ] `NEXT_PUBLIC_SITE_URL=https://seudominio.com`
- [ ] `NEXT_PUBLIC_ADMIN_API_URL=https://api.seudominio.com`

Depois de trocar o `.env`:
```bash
# api só precisa reiniciar (lê env em runtime)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps api

# frontend/admin precisam de rebuild SEM CACHE — o Docker não invalida a
# camada de build só porque uma env var mudou (nada nos arquivos-fonte
# mudou), e next build faz SSG/ISR da home usando os dados que pegar no
# momento do build. Rebuild com cache = continua servindo o HTML antigo
# (`x-nextjs-cache: HIT` na resposta é o sintoma).
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache frontend admin
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps frontend admin
```

Depois do rebuild, ainda pode sobrar cache em dois lugares — sem isso, a
home continua com URL antiga mesmo com tudo redeployado:
- **Redis** (server-side, `home-sections` etc.): `INCR ecom:cver:catalog` e
  `INCR ecom:cver:product` dentro do `cater-redis` invalida tudo do
  catálogo num passo só (sem apagar carrinho/sessão, que ficam noutra
  chave).
- **ISR do Next** (por página): `POST /api/revalidate?tag=products,banners,theme,categories`
  com o header `x-revalidate-secret: $REVALIDATE_SECRET` (valor no `.env`).

### Se a Cloudflare estiver com o proxy (nuvem laranja) ligado antes do SSL sair
Enquanto o site não tem certificado próprio, deixar o proxy da Cloudflare
ligado pode dar **erro 521 ("Web server is down")**, porque ela tenta falar
HTTPS com a origem e ainda não tem o que validar. Solução rápida: desligar o
proxy (nuvem cinza, "DNS only") nos três registros até o SSL sair, religar
depois. Dá pra fazer via API (`PATCH /zones/{zona}/dns_records/{id}` com
`"proxied": false`) sem precisar entrar no dashboard.

### Se o navegador der "Failed to fetch" no login do admin mesmo com o backend ok
Testar direto com `curl` primeiro — se o backend responder normal (CORS
correto, resposta HTTP válida) mas o navegador falhar, é sessão/cache do
navegador daquela aba específica (de quando o domínio ainda estava quebrado
mais cedo), não um problema real de servidor. Testar em janela anônima
resolve/confirma.

## Detalhes técnicos do aaPanel (pra quem for mexer no código depois)

- **Não existe** uma ação de API `CreateProxy` que funcione — ela é pensada
  pra sites em nginx; nesta instância (OpenLiteSpeed) devolve 404 puro. O
  jeito que funciona: escrever o contexto de proxy reverso **direto no
  arquivo** que o vhost já inclui
  (`/www/server/panel/vhost/openlitespeed/proxy/<host>/proxy.conf`, via
  `/files?action=CreateFile` + `SaveFileBody`) e recarregar o LiteSpeed
  (`/system?action=ServiceAdmin`, `name=openlitespeed`, `type=restart`).
- Emitir SSL é `CreateLet` (não `ApplyCertApi`, que não existe) —
  `domains` é uma **lista JSON** (`["host"]`), não string separada por
  vírgula.
- **aaPanel recusa `CreateLet` se o site tiver "proxy reverso" ligado** pelo
  mecanismo *oficial* dele (tela "Reverse proxy" do painel) — mensagem
  literal "Sites that have reverse proxy turned on cannot request SSL!".
  Escrever o arquivo por baixo (acima) **não** aciona esse flag, então SSL
  funciona normalmente — mas se alguém um dia usar a tela do aaPanel pra
  adicionar o proxy manualmente, precisa **tirar** de lá antes de tentar
  emitir certificado.
- A validação HTTP-01 do Let's Encrypt bate em
  `http://<host>/.well-known/acme-challenge/<token>`. Como o contexto `/` é
  proxy reverso (tudo vai pro container), essa validação cairia 404 no
  Next.js/FastAPI se não abrir uma exceção **estática** pra esse caminho
  específico — por isso o `proxy.conf` sempre nasce com um `context
  /.well-known/acme-challenge/` servindo local, antes do `context /` de
  proxy.

## Resto do checklist (não muda com domínio)

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

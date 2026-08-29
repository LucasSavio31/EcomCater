# Módulos

| slug | label | tipo | togglável | responsabilidade |
|---|---|---|---|---|
| `products` | Produtos | domain | não | CRUD de produto, variações/SKU, opções, imagens, specs, relacionados, reviews, busca |
| `categories` | Categorias | domain | não | árvore de categorias, slug/path |
| `cart` | Carrinho | domain | não | carrinho persistente (convidado/logado), snapshot de preço, totais, estado de checkout |
| `orders` | Pedidos | domain | não | criação a partir do carrinho, máquina de estados, linha do tempo, gestão admin |
| `customers` | Clientes | domain | não | auth de cliente, perfil, endereços, histórico |
| `payment` | Pagamento | feature | **sim** | interface `PaymentGateway`; provider **Appmax** (cartão/Pix/boleto); webhook idempotente |
| `shipping` | Frete | feature | **sim** | interface `ShippingProvider`; provider **Melhor Envio** (cotação); cache Redis; webhook de rastreio |
| `promotions` | Promoções | feature | **sim** | cupons (percent/fixed/free_shipping), limites, resgates |
| `banners` | Banners | feature | **sim** | vitrines da home por slot e período |
| `menus` | Menus | domain | não | menu superior (mega menu + atalhos de tamanho) e rodapé |
| `theme` | Aparência | domain | não | tema visual (singleton), páginas institucionais |
| `newsletter` | Newsletter | feature | **sim** | captura de e-mail, opt-in |
| `admin` | Administração | domain | não | auth administrativa, usuários/papéis, dashboard, settings gerais, registro de módulos |

## Contrato de um módulo

```
modules/<slug>/
  module.py          register(ModuleSpec(...))
  models.py          modelos SQLAlchemy
  schemas.py         DTOs Pydantic (entrada/saída) — compartilhados loja/admin
  service.py         REGRA DE NEGÓCIO (fonte única da verdade)
  repository.py      queries complexas (opcional)
  events.py          publishers/subscribers do event bus (opcional)
  config.py          Pydantic model das configs persistidas (se togglável)
  router_public.py   -> /api/<slug>/...
  router_admin.py    -> /api/admin/<slug>/...
  providers/         só payment e shipping
    base.py          interface abstrata (ABC)
    <provider>.py    implementação concreta
```

## Providers

### Pagamento — `PaymentGateway` (ABC)
- `create_charge(order, method, ...) -> Charge`
- `parse_webhook(headers, body) -> WebhookResult`
- `refund(payment, amount) -> RefundResult`
- Provider real: **Appmax** (API v2, https://docs.appmax.com.br/api-reference/introduction).
  Autentica só com o **token Appmax**. Webhooks levam o pedido a
  `PAGO` / `AGUARDANDO PAGAMENTO` / `CANCELADO`. Métodos: PIX, cartão de crédito, boleto.
  Mesmo comportamento já usado no SaaS Psiqio.

### Frete — `ShippingProvider` (ABC)
- `quote(origin, dest, packages) -> list[ShippingRate]`
- Provider real: **Melhor Envio** (https://docs.melhorenvio.com.br/docs/introducao-a-api).
  Cotação com cache em Redis. Webhooks de rastreio atualizam o pedido para
  `POSTADO` / `EM TRÂNSITO` / `ENTREGUE`.

Adicionar provider = novo arquivo em `providers/` + registro no `module.py`. Nada
mais no sistema muda.

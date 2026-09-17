"""Definições de cache da Cloudflare por tipo de página da loja.

Só se aplica ao domínio **raiz** (a loja) — `admin.` e `api.` nunca entram
nessas regras, ficam sempre em bypass explícito.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CachePageDef:
    label: str
    # caminho literal (sem barra final) ou prefixo — ver `_expression`
    path: str
    is_prefix: bool
    ttl_seconds: int
    description: str


# Ordem = ordem de exibição no admin.
CACHE_PAGE_DEFS: dict[str, CachePageDef] = {
    "home": CachePageDef(
        label="Início",
        path="/",
        is_prefix=False,
        ttl_seconds=300,
        description="Banners e vitrines da home.",
    ),
    "categoria": CachePageDef(
        label="Categorias (vitrine)",
        path="/categoria/",
        is_prefix=True,
        ttl_seconds=300,
        description="Listagem de produtos por categoria.",
    ),
    "produto": CachePageDef(
        label="Página de produto",
        path="/produto/",
        is_prefix=True,
        ttl_seconds=120,
        description="Cada produto é uma URL própria — cacheada individualmente, "
        "com tempo curto pra refletir mudança de preço/estoque logo.",
    ),
    "pagina": CachePageDef(
        label="Páginas institucionais",
        path="/pagina/",
        is_prefix=True,
        ttl_seconds=3600,
        description='Ex.: "Quem somos", trocas, política de privacidade.',
    ),
    "busca": CachePageDef(
        label="Busca",
        path="/busca",
        is_prefix=True,
        ttl_seconds=60,
        description="Resultado de busca — TTL curto por ser muito variável.",
    ),
}

# Nunca cacheados — não é uma opção do usuário, é regra fixa.
_ALWAYS_BYPASS_PATHS = [
    "/carrinho",
    "/checkout",
    "/minha-conta",
    "/favoritos",
    "/esqueci-senha",
    "/redefinir-senha",
]


def _expr(hostname: str, path: str, *, is_prefix: bool) -> str:
    host_cond = f'http.host eq "{hostname}"'
    if path == "/":
        path_cond = 'http.request.uri.path eq "/"'
    elif is_prefix:
        path_cond = f'starts_with(http.request.uri.path, "{path}")'
    else:
        path_cond = f'http.request.uri.path eq "{path}"'
    return f"({host_cond} and {path_cond})"


def build_rules(hostname: str, selected_pages: list[str]) -> list[dict]:
    """Monta as regras da fase `http_request_cache_settings` pro domínio raiz.

    Bypass primeiro (carrinho/checkout/conta/etc. + admin./api.), depois uma
    regra de cache por tipo de página selecionado.
    """
    rules: list[dict] = []

    for path in _ALWAYS_BYPASS_PATHS:
        rules.append(
            {
                "expression": _expr(hostname, path, is_prefix=True),
                "description": f"bypass: {path}",
                "action": "set_cache_settings",
                "action_parameters": {"cache": False},
            }
        )

    # admin./api. nunca cacheados por este ruleset, mesmo que algum dia
    # compartilhem zona com paths parecidos.
    for sub in (f"admin.{hostname}", f"api.{hostname}"):
        rules.append(
            {
                "expression": f'(http.host eq "{sub}")',
                "description": f"bypass: {sub}",
                "action": "set_cache_settings",
                "action_parameters": {"cache": False},
            }
        )

    for key in selected_pages:
        page = CACHE_PAGE_DEFS.get(key)
        if page is None:
            continue
        rules.append(
            {
                "expression": _expr(hostname, page.path, is_prefix=page.is_prefix),
                "description": f"cache: {key}",
                "action": "set_cache_settings",
                "action_parameters": {
                    "cache": True,
                    "edge_ttl": {"mode": "override_origin", "default": page.ttl_seconds},
                },
            }
        )

    return rules

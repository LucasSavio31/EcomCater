"""Ponto único de import de todos os modelos.

O Alembic (autogenerate) e qualquer `Base.metadata.create_all` dependem de que
todas as classes tenham sido importadas. Importe SEMPRE daqui em scripts/testes.
"""
from __future__ import annotations

from app.shared.models_base import Base  # noqa: F401

# --- customers ---
from app.modules.customers.models import (  # noqa: F401
    CustomerAddress,
    User,
    Wishlist,
    WishlistItem,
)

# --- admin / infra ---
from app.modules.admin.models import (  # noqa: F401
    AdminUser,
    AuthRefreshToken,
    EmailLog,
    ModuleRow,
    SmtpSettings,
    StoreSettings,
)

# --- categories ---
from app.modules.categories.models import Category  # noqa: F401

# --- products ---
from app.modules.products.models import (  # noqa: F401
    Product,
    ProductCategory,
    ProductImage,
    ProductRelated,
    ProductReview,
    ProductSpec,
    ProductVariant,
    ProductVariantOption,
    VariantOptionType,
    VariantOptionValue,
)

# --- cart ---
from app.modules.cart.models import Cart, CartItem  # noqa: F401

# --- promotions ---
from app.modules.promotions.models import Coupon, CouponRedemption  # noqa: F401

# --- orders ---
from app.modules.orders.models import Order, OrderEvent, OrderItem  # noqa: F401

# --- payment ---
from app.modules.payment.models import Payment, PaymentWebhookEvent  # noqa: F401

# --- shipping ---
from app.modules.shipping.models import ShippingQuote  # noqa: F401

# --- banners ---
from app.modules.banners.models import Banner  # noqa: F401

# --- menus ---
from app.modules.menus.models import Menu, MenuItem  # noqa: F401

# --- theme ---
from app.modules.theme.models import Page, ThemeSettings  # noqa: F401

# --- newsletter ---
from app.modules.newsletter.models import NewsletterSubscriber  # noqa: F401

# --- cart recovery ---
from app.modules.cart_recovery.models import (  # noqa: F401
    AbandonedCart,
    RecoveryMessage,
)

# --- analytics ---
from app.modules.analytics.models import AnalyticsSettings  # noqa: F401

__all__ = ["Base"]

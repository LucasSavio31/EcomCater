# Referência da API

Gerado do OpenAPI. Base local: http://localhost:8000  ·  Swagger: /docs

## admin:admin

| Método | Rota | |
|---|---|---|
| POST | `/api/admin/auth/change-password` | Change Password |
| POST | `/api/admin/auth/login` | Login |
| POST | `/api/admin/auth/logout` | Logout |
| GET | `/api/admin/auth/me` | Me |
| POST | `/api/admin/auth/refresh` | Refresh |
| GET | `/api/admin/dashboard` | Dashboard |
| GET | `/api/admin/modules` | List Modules |
| PATCH | `/api/admin/modules/{slug}` | Update Module |
| GET | `/api/admin/settings` | Get Settings |
| PUT | `/api/admin/settings` | Update Settings |
| GET | `/api/admin/smtp` | Get Smtp |
| PUT | `/api/admin/smtp` | Update Smtp |
| POST | `/api/admin/smtp/test` | Test Smtp |
| GET | `/api/admin/users` | List Users |
| POST | `/api/admin/users` | Create User |
| PATCH | `/api/admin/users/{user_id}` | Update User |

## admin:banners

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/banners` | Admin List |
| POST | `/api/admin/banners` | Create Banner |
| DELETE | `/api/admin/banners/{banner_id}` | Delete Banner |
| PATCH | `/api/admin/banners/{banner_id}` | Update Banner |
| POST | `/api/admin/banners/{banner_id}/image` | Upload Image |

## admin:categories

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/categories` | List Categories |
| POST | `/api/admin/categories` | Create Category |
| POST | `/api/admin/categories/reorder` | Reorder |
| GET | `/api/admin/categories/tree` | Admin Tree |
| DELETE | `/api/admin/categories/{category_id}` | Delete Category |
| GET | `/api/admin/categories/{category_id}` | Get Category |
| PATCH | `/api/admin/categories/{category_id}` | Update Category |
| POST | `/api/admin/categories/{category_id}/image` | Upload Image |

## admin:customers

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/customers/_ping` |  Ping Admin |

## admin:menus

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/menus` | List Menus |
| POST | `/api/admin/menus` | Create Menu |
| POST | `/api/admin/menus/items/reorder` | Reorder |
| DELETE | `/api/admin/menus/items/{item_id}` | Delete Item |
| PATCH | `/api/admin/menus/items/{item_id}` | Update Item |
| GET | `/api/admin/menus/{location}/resolved` | Resolved |
| PATCH | `/api/admin/menus/{menu_id}` | Update Menu |
| POST | `/api/admin/menus/{menu_id}/items` | Add Item |

## admin:newsletter

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/newsletter` | List Subscribers |

## admin:orders

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/orders` | List Orders |
| GET | `/api/admin/orders/{number}` | Get Order |
| POST | `/api/admin/orders/{number}/notes` | Add Note |
| POST | `/api/admin/orders/{number}/status` | Change Status |

## admin:payment

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/payment/config` | Get Config |
| PUT | `/api/admin/payment/config` | Update Config |
| GET | `/api/admin/payment/payments` | List Payments |
| POST | `/api/admin/payment/refund/{order_number}` | Refund |
| GET | `/api/admin/payment/webhook-events` | Webhook Events |
| POST | `/api/admin/payment/webhook-events/{event_id}/reprocess` | Reprocess |

## admin:products

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/products` | List Products |
| POST | `/api/admin/products` | Create Product |
| DELETE | `/api/admin/products/{product_id}` | Delete Product |
| GET | `/api/admin/products/{product_id}` | Get Product |
| PATCH | `/api/admin/products/{product_id}` | Update Product |
| POST | `/api/admin/products/{product_id}/images` | Add Image |
| POST | `/api/admin/products/{product_id}/images/reorder` | Reorder Images |
| DELETE | `/api/admin/products/{product_id}/images/{image_id}` | Delete Image |
| PUT | `/api/admin/products/{product_id}/option-types` | Set Option Types |
| GET | `/api/admin/products/{product_id}/reviews` | List Reviews |
| POST | `/api/admin/products/{product_id}/reviews/{review_id}/moderate` | Moderate Review |
| PUT | `/api/admin/products/{product_id}/specs` | Replace Specs |
| POST | `/api/admin/products/{product_id}/status` | Set Status |
| POST | `/api/admin/products/{product_id}/variants` | Create Variant |
| DELETE | `/api/admin/products/{product_id}/variants/{variant_id}` | Delete Variant |
| PATCH | `/api/admin/products/{product_id}/variants/{variant_id}` | Update Variant |

## admin:promotions

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/promotions` | List Coupons |
| POST | `/api/admin/promotions` | Create Coupon |
| DELETE | `/api/admin/promotions/{coupon_id}` | Delete Coupon |
| PATCH | `/api/admin/promotions/{coupon_id}` | Update Coupon |

## admin:shipping

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/shipping/config` | Get Config |
| PUT | `/api/admin/shipping/config` | Update Config |
| POST | `/api/admin/shipping/test-quote` | Test Quote |

## admin:theme

| Método | Rota | |
|---|---|---|
| GET | `/api/admin/theme` | Get Theme |
| PUT | `/api/admin/theme` | Update Theme |
| POST | `/api/admin/theme/image/{kind}` | Upload Theme Image |
| GET | `/api/admin/theme/pages` | List Pages |
| POST | `/api/admin/theme/pages` | Create Page |
| DELETE | `/api/admin/theme/pages/{page_id}` | Delete Page |
| PATCH | `/api/admin/theme/pages/{page_id}` | Update Page |

## banners

| Método | Rota | |
|---|---|---|
| GET | `/api/banners` | List Banners |

## cart

| Método | Rota | |
|---|---|---|
| GET | `/api/cart` | Get Cart |
| DELETE | `/api/cart/coupon` | Remove Coupon |
| POST | `/api/cart/coupon` | Apply Coupon |
| POST | `/api/cart/items` | Add Item |
| DELETE | `/api/cart/items/{item_id}` | Remove Item |
| PATCH | `/api/cart/items/{item_id}` | Update Item |
| POST | `/api/cart/shipping` | Select Shipping |
| GET | `/api/cart/shipping-options` | Shipping Options |
| PUT | `/api/cart/zip` | Set Zip |

## categories

| Método | Rota | |
|---|---|---|
| GET | `/api/categories/by-path/{path}` | Get By Path |
| GET | `/api/categories/tree` | Get Tree |
| GET | `/api/categories/{slug}` | Get By Slug |

## customers

| Método | Rota | |
|---|---|---|
| POST | `/api/customers/auth/login` | Login |
| POST | `/api/customers/auth/logout` | Logout |
| POST | `/api/customers/auth/refresh` | Refresh |
| POST | `/api/customers/auth/register` | Register |
| GET | `/api/customers/me` | Me |
| PATCH | `/api/customers/me` | Update Me |
| GET | `/api/customers/me/addresses` | List Addresses |
| POST | `/api/customers/me/addresses` | Create Address |
| DELETE | `/api/customers/me/addresses/{address_id}` | Delete Address |
| PATCH | `/api/customers/me/addresses/{address_id}` | Update Address |
| GET | `/api/customers/me/wishlist` | Get Wishlist |
| DELETE | `/api/customers/me/wishlist/{product_id}` | Remove Wishlist |
| POST | `/api/customers/me/wishlist/{product_id}` | Add Wishlist |

## menus

| Método | Rota | |
|---|---|---|
| GET | `/api/menus/{location}` | Get Menu |

## meta

| Método | Rota | |
|---|---|---|
| GET | `/health` | Health |

## newsletter

| Método | Rota | |
|---|---|---|
| POST | `/api/newsletter/subscribe` | Subscribe |
| GET | `/api/newsletter/unsubscribe` | Unsubscribe |

## orders

| Método | Rota | |
|---|---|---|
| GET | `/api/orders` | My Orders |
| POST | `/api/orders/checkout` | Checkout |
| GET | `/api/orders/{number}` | Get Order |

## payment

| Método | Rota | |
|---|---|---|
| POST | `/api/payment/charge` | Charge |
| GET | `/api/payment/status/{order_number}` | Status |

## products

| Método | Rota | |
|---|---|---|
| GET | `/api/products` | List Products |
| GET | `/api/products/featured` | Featured |
| GET | `/api/products/search` | Search |
| GET | `/api/products/{slug}` | Get Product |
| POST | `/api/products/{slug}/reviews` | Create Review |

## shipping

| Método | Rota | |
|---|---|---|
| POST | `/api/shipping/quote` | Quote |

## theme

| Método | Rota | |
|---|---|---|
| GET | `/api/theme` | Get Theme |
| GET | `/api/theme/pages/{slug}` | Get Page |

## webhook:payment

| Método | Rota | |
|---|---|---|
| POST | `/api/webhooks/payment/{provider}` | Payment Webhook |

## webhook:shipping

| Método | Rota | |
|---|---|---|
| POST | `/api/webhooks/shipping/melhor-envio` | Melhor Envio Webhook |

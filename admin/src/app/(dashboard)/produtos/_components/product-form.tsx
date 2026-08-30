'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, Card, Input } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { Tabs, type TabDef } from '@/components/tabs';
import { Checkbox, Select, Textarea } from '@/components/form-controls';
import { StatusBadge } from '@/components/status-badge';
import { useToast } from '@/components/toast';
import { centsToInput, inputToCents, slugify } from '@/lib/format';
import { productsApi } from '@/modules/catalog/api';
import type { Category, ProductDetail, ProductInput, ProductStatus } from '@/modules/catalog/types';
import { VariantsTab } from './variants-tab';
import { ImagesTab } from './images-tab';
import { SpecsTab } from './specs-tab';
import { RelatedTab } from './related-tab';
import { ReviewsTab } from './reviews-tab';

interface GeneralState {
  name: string;
  brand: string;
  supplier: string;
  category_id: string;
  extra_category_ids: string[];
  short_description: string;
  description: string;
  is_featured: boolean;
  price: string;
  compare_at_price: string;
  pix_discount_pct: string;
  installments_max: string;
  weight_grams: string;
  length_mm: string;
  width_mm: string;
  height_mm: string;
  seo_title: string;
  seo_description: string;
}

function toState(p: ProductDetail | null): GeneralState {
  return {
    name: p?.name ?? '',
    brand: p?.brand ?? '',
    supplier: p?.supplier ?? '',
    category_id: p?.category_id ?? '',
    extra_category_ids: p?.extra_category_ids ?? [],
    short_description: p?.short_description ?? '',
    description: p?.description ?? '',
    is_featured: p?.is_featured ?? false,
    price: centsToInput(p?.price_cents ?? null),
    compare_at_price: centsToInput(p?.compare_at_price_cents ?? null),
    pix_discount_pct: p?.pix_discount_pct != null ? String(p.pix_discount_pct) : '',
    installments_max: p?.installments_max != null ? String(p.installments_max) : '',
    weight_grams: p?.weight_grams != null ? String(p.weight_grams) : '0',
    length_mm: p?.length_mm != null ? String(p.length_mm) : '0',
    width_mm: p?.width_mm != null ? String(p.width_mm) : '0',
    height_mm: p?.height_mm != null ? String(p.height_mm) : '0',
    seo_title: p?.seo_title ?? '',
    seo_description: p?.seo_description ?? '',
  };
}

function buildPayload(s: GeneralState, status: ProductStatus): ProductInput {
  return {
    name: s.name.trim(),
    brand: s.brand.trim() || null,
    supplier: s.supplier.trim() || null,
    category_id: s.category_id || null,
    extra_category_ids: s.extra_category_ids,
    status,
    price_cents: inputToCents(s.price) ?? 0,
    compare_at_price_cents: inputToCents(s.compare_at_price),
    pix_discount_pct: s.pix_discount_pct ? Number(s.pix_discount_pct) : null,
    installments_max: s.installments_max ? Number(s.installments_max) : null,
    short_description: s.short_description.trim() || null,
    description: s.description.trim() || null,
    is_featured: s.is_featured,
    weight_grams: Number(s.weight_grams) || 0,
    length_mm: Number(s.length_mm) || 0,
    width_mm: Number(s.width_mm) || 0,
    height_mm: Number(s.height_mm) || 0,
    seo_title: s.seo_title.trim() || null,
    seo_description: s.seo_description.trim() || null,
  };
}

interface ProductFormProps {
  product: ProductDetail | null;
  categories: Category[];
  onSaved: (p: ProductDetail) => void;
}

export function ProductForm({ product, categories, onSaved }: ProductFormProps) {
  const router = useRouter();
  const toast = useToast();
  const isNew = product === null;

  const [state, setState] = useState<GeneralState>(() => toState(product));
  const [status, setStatus] = useState<ProductStatus>(product?.status ?? 'draft');
  const [tab, setTab] = useState('geral');
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const set = <K extends keyof GeneralState>(key: K, value: GeneralState[K]): void =>
    setState((prev) => ({ ...prev, [key]: value }));

  const categoryOptions = categories.map((c) => ({
    value: c.id,
    label: c.path ? c.path.replace(/\//g, ' › ') : c.name,
  }));

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!state.name.trim()) next.name = 'Informe o nome do produto.';
    if (inputToCents(state.price) == null) next.price = 'Informe um preço válido.';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSave(): Promise<void> {
    if (!validate()) {
      setTab('geral');
      return;
    }
    setSaving(true);
    const payload = buildPayload(state, status);
    const result = isNew
      ? await productsApi.create(payload)
      : await productsApi.update(product.id, payload);
    setSaving(false);

    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success(isNew ? 'Produto criado.' : 'Produto salvo.');
    onSaved(result.data);
    if (isNew) router.replace(`/produtos/${result.data.id}`);
  }

  async function handleStatus(value: ProductStatus): Promise<void> {
    if (isNew) {
      setStatus(value);
      return;
    }
    const result = await productsApi.setStatus(product.id, value);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    setStatus(value);
    onSaved(result.data);
    toast.success('Status atualizado.');
  }

  // O mesmo conjunto de abas para todo produto (novo ou existente).
  const tabs: TabDef[] = [
    { id: 'geral', label: 'Geral' },
    { id: 'preco', label: 'Preço' },
    { id: 'variacoes', label: 'Variações' },
    { id: 'imagens', label: 'Imagens' },
    { id: 'specs', label: 'Especificações' },
    { id: 'relacionados', label: 'Relacionados' },
    { id: 'seo', label: 'SEO' },
    { id: 'avaliacoes', label: 'Avaliações' },
  ];

  const NeedsSave = () => (
    <div className="rounded-card border border-dashed border-surface-border p-6 text-center text-sm text-text-muted">
      Salve o produto primeiro para gerenciar esta seção.
      <div className="mt-3">
        <Button size="sm" loading={saving} onClick={() => void handleSave()}>
          Criar produto
        </Button>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={isNew ? 'Novo produto' : state.name || 'Produto'}
        back={
          <button
            type="button"
            onClick={() => router.push('/produtos')}
            className="self-start text-sm text-accent hover:underline"
          >
            ← Voltar para produtos
          </button>
        }
        description={
          !isNew && (
            <span className="inline-flex items-center gap-2">
              <StatusBadge kind="product" value={status} />
              <span className="text-text-muted">/{product.slug}</span>
            </span>
          )
        }
        actions={
          <div className="flex flex-wrap gap-2">
            {!isNew && status !== 'active' && (
              <Button onClick={() => void handleStatus('active')}>Publicar</Button>
            )}
            {!isNew && status === 'active' && (
              <Button variant="outline" onClick={() => void handleStatus('archived')}>
                Arquivar
              </Button>
            )}
            {!isNew && status === 'archived' && (
              <Button variant="outline" onClick={() => void handleStatus('draft')}>
                Voltar a rascunho
              </Button>
            )}
            <Button loading={saving} onClick={() => void handleSave()}>
              {isNew ? 'Criar produto' : 'Salvar'}
            </Button>
          </div>
        }
      />

      <Tabs tabs={tabs} active={tab} onChange={setTab}>
        {tab === 'geral' && (
          <Card variant="outline" className="flex flex-col gap-4">
            <Input
              label="Nome"
              required
              value={state.name}
              error={errors.name}
              onChange={(e) => set('name', e.target.value)}
              hint={state.name ? `slug: ${slugify(state.name)}` : undefined}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <Input label="Marca" value={state.brand} onChange={(e) => set('brand', e.target.value)} />
              <Input label="Fornecedor (uso interno)" hint="Não aparece na loja. Usado para separar PDFs e etiquetas." value={state.supplier} onChange={(e) => set('supplier', e.target.value)} />
              <Select
                label="Categoria principal"
                value={state.category_id}
                onChange={(e) => set('category_id', e.target.value)}
                placeholder="Sem categoria"
                options={categoryOptions}
              />
            </div>
            <fieldset className="flex flex-col gap-2 rounded-card border border-surface-border p-3">
              <legend className="px-1 text-sm font-medium">Categorias adicionais</legend>
              <div className="flex flex-wrap gap-2">
                {categories.length === 0 && <span className="text-sm text-text-muted">Nenhuma categoria.</span>}
                {categories.map((c) => {
                  const checked = state.extra_category_ids.includes(c.id);
                  return (
                    <label
                      key={c.id}
                      className="flex items-center gap-1.5 rounded-card border border-surface-border px-2 py-1 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) =>
                          set(
                            'extra_category_ids',
                            e.target.checked
                              ? [...state.extra_category_ids, c.id]
                              : state.extra_category_ids.filter((id) => id !== c.id),
                          )
                        }
                      />
                      {c.name}
                    </label>
                  );
                })}
              </div>
            </fieldset>
            <Textarea
              label="Descrição curta"
              value={state.short_description}
              onChange={(e) => set('short_description', e.target.value)}
              rows={2}
            />
            <Textarea
              label="Descrição completa"
              value={state.description}
              onChange={(e) => set('description', e.target.value)}
              rows={6}
              hint="HTML simples é aceito."
            />
            <Checkbox
              label="Produto em destaque"
              checked={state.is_featured}
              onChange={(v) => set('is_featured', v)}
            />
          </Card>
        )}

        {tab === 'preco' && (
          <Card variant="outline" className="flex flex-col gap-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Preço promocional (R$)"
                required
                inputMode="decimal"
                hint="O valor que o cliente paga."
                value={state.price}
                error={errors.price}
                onChange={(e) => set('price', e.target.value)}
              />
              <Input
                label="Preço “de” / normal (R$)"
                inputMode="decimal"
                hint="Vazio = sem desconto."
                value={state.compare_at_price}
                onChange={(e) => set('compare_at_price', e.target.value)}
              />
            </div>
            {(() => {
              const now = Number(String(state.price).replace(',', '.'));
              const was = Number(String(state.compare_at_price).replace(',', '.'));
              if (!(was > now && now > 0)) return null;
              const pct = Math.round((1 - now / was) * 100);
              return (
                <p className="text-sm">
                  Selo de desconto:{' '}
                  <span className="rounded bg-danger px-1.5 py-0.5 text-xs font-bold text-white">
                    -{pct}%
                  </span>{' '}
                  <span className="text-text-muted">(liga/desliga em Aparência › Comportamento)</span>
                </p>
              );
            })()}
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Desconto Pix (%)"
                inputMode="decimal"
                value={state.pix_discount_pct}
                onChange={(e) => set('pix_discount_pct', e.target.value)}
              />
              <Input
                label="Máx. de parcelas"
                inputMode="numeric"
                value={state.installments_max}
                onChange={(e) => set('installments_max', e.target.value)}
              />
            </div>
            <h3 className="text-sm font-semibold">Dimensões para frete</h3>
            <div className="grid gap-4 sm:grid-cols-4">
              <Input
                label="Peso (g)"
                inputMode="numeric"
                value={state.weight_grams}
                onChange={(e) => set('weight_grams', e.target.value)}
              />
              <Input
                label="Comp. (mm)"
                inputMode="numeric"
                value={state.length_mm}
                onChange={(e) => set('length_mm', e.target.value)}
              />
              <Input
                label="Larg. (mm)"
                inputMode="numeric"
                value={state.width_mm}
                onChange={(e) => set('width_mm', e.target.value)}
              />
              <Input
                label="Alt. (mm)"
                inputMode="numeric"
                value={state.height_mm}
                onChange={(e) => set('height_mm', e.target.value)}
              />
            </div>
          </Card>
        )}

        {tab === 'seo' && (
          <Card variant="outline" className="flex flex-col gap-4">
            <Input
              label="Título SEO"
              value={state.seo_title}
              onChange={(e) => set('seo_title', e.target.value)}
            />
            <Textarea
              label="Descrição SEO"
              value={state.seo_description}
              onChange={(e) => set('seo_description', e.target.value)}
              rows={3}
            />
          </Card>
        )}

        {tab === 'variacoes' &&
          (product ? <VariantsTab product={product} onChanged={onSaved} /> : <NeedsSave />)}
        {tab === 'imagens' &&
          (product ? <ImagesTab product={product} onChanged={onSaved} /> : <NeedsSave />)}
        {tab === 'specs' &&
          (product ? <SpecsTab product={product} onChanged={onSaved} /> : <NeedsSave />)}
        {tab === 'relacionados' &&
          (product ? <RelatedTab product={product} onChanged={onSaved} /> : <NeedsSave />)}
        {tab === 'avaliacoes' &&
          (product ? <ReviewsTab productId={product.id} /> : <NeedsSave />)}
      </Tabs>

      {isNew && (
        <p className="text-sm text-text-muted">
          Salve o produto para liberar as abas de variações, imagens, especificações e avaliações.
        </p>
      )}
    </div>
  );
}

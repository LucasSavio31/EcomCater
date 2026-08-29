/** Consulta de CEP na ViaCEP (pública, sem chave) para autopreencher endereço. */

export interface CepAddress {
  street: string;
  district: string;
  city: string;
  state: string;
}

export async function lookupCep(rawZip: string): Promise<CepAddress | null> {
  const zip = rawZip.replace(/\D/g, '');
  if (zip.length !== 8) return null;
  try {
    const res = await fetch(`https://viacep.com.br/ws/${zip}/json/`, { cache: 'force-cache' });
    if (!res.ok) return null;
    const data = (await res.json()) as {
      erro?: boolean;
      logradouro?: string;
      bairro?: string;
      localidade?: string;
      uf?: string;
    };
    if (data.erro) return null;
    return {
      street: data.logradouro ?? '',
      district: data.bairro ?? '',
      city: data.localidade ?? '',
      state: (data.uf ?? '').toUpperCase(),
    };
  } catch {
    return null;
  }
}

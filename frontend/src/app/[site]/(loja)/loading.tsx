import { Spinner } from '@ecom/ui';

export default function Loading() {
  return (
    <div className="flex justify-center py-20">
      <Spinner size="lg" label="Carregando…" />
    </div>
  );
}

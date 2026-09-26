import { Spinner } from '@ecom/ui';

export default function Loading() {
  return (
    <div className="flex justify-center py-16">
      <Spinner size="lg" label="Carregando produto…" />
    </div>
  );
}

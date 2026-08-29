'use client';

import { useState } from 'react';
import { Badge, Button, Card, Input, Modal } from '@ecom/ui';
import { PageHeader } from '@/components/page-header';
import { DataTable, type Column } from '@/components/data-table';
import { AsyncBoundary } from '@/components/async-boundary';
import { Checkbox, Select } from '@/components/form-controls';
import { useToast } from '@/components/toast';
import { useResource } from '@/lib/use-resource';
import { formatDateTime } from '@/lib/format';
import { useAdminAuth, type AdminRole } from '@/modules/auth';
import { usersApi, type AdminUserRow } from '@/modules/users/api';

const ROLE_OPTIONS: Array<{ value: AdminRole; label: string }> = [
  { value: 'staff', label: 'Staff' },
  { value: 'admin', label: 'Admin' },
  { value: 'super_admin', label: 'Super admin' },
];

const ROLE_LABEL: Record<AdminRole, string> = {
  staff: 'Staff',
  admin: 'Admin',
  super_admin: 'Super admin',
};

export default function UsuariosPage() {
  const toast = useToast();
  const { user } = useAdminAuth();
  const isSuperAdmin = user?.role === 'super_admin';
  const { data, loading, error, reload } = useResource(() => usersApi.list());

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<AdminUserRow | null>(null);

  const columns: Array<Column<AdminUserRow>> = [
    { key: 'name', header: 'Nome', primary: true, cell: (u) => u.name },
    { key: 'email', header: 'E-mail', cell: (u) => u.email },
    { key: 'role', header: 'Papel', cell: (u) => <Badge tone="neutral">{ROLE_LABEL[u.role]}</Badge> },
    {
      key: 'active',
      header: 'Ativo',
      cell: (u) => (u.is_active ? <Badge tone="success">Sim</Badge> : <Badge tone="danger">Não</Badge>),
    },
    { key: 'last', header: 'Último login', cell: (u) => formatDateTime(u.last_login_at) },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Usuários"
        description="Contas administrativas e papéis."
        actions={
          isSuperAdmin ? (
            <Button onClick={() => setCreating(true)}>Novo usuário</Button>
          ) : undefined
        }
      />

      {!isSuperAdmin && (
        <Card variant="outline" className="text-sm text-text-muted">
          Apenas um super admin pode criar novas contas. Você pode editar as contas existentes conforme seu papel.
        </Card>
      )}

      <AsyncBoundary loading={loading} error={error} onRetry={reload}>
        <DataTable
          columns={columns}
          rows={data ?? []}
          rowKey={(u) => u.id}
          emptyMessage="Nenhum usuário."
          rowActions={(u) => (
            <Button size="sm" variant="outline" onClick={() => setEditing(u)}>
              Editar
            </Button>
          )}
        />
      </AsyncBoundary>

      {creating && (
        <CreateUserModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            reload();
          }}
        />
      )}
      {editing && (
        <EditUserModal
          user={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </div>
  );
}

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<AdminRole>('staff');
  const [saving, setSaving] = useState(false);

  async function submit(): Promise<void> {
    if (!email.trim() || !name.trim() || password.length < 8) {
      toast.error('Preencha nome, e-mail e uma senha de ao menos 8 caracteres.');
      return;
    }
    setSaving(true);
    const result = await usersApi.create({ email: email.trim(), name: name.trim(), password, role });
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Usuário criado.');
    onCreated();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Novo usuário"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button loading={saving} onClick={() => void submit()}>
            Criar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Input label="Nome" required value={name} onChange={(e) => setName(e.target.value)} />
        <Input label="E-mail" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Input
          label="Senha"
          type="password"
          required
          hint="Mínimo de 8 caracteres."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Select
          label="Papel"
          value={role}
          options={ROLE_OPTIONS}
          onChange={(e) => setRole(e.target.value as AdminRole)}
        />
      </div>
    </Modal>
  );
}

function EditUserModal({
  user,
  onClose,
  onSaved,
}: {
  user: AdminUserRow;
  onClose: () => void;
  onSaved: () => void;
}) {
  const toast = useToast();
  const { user: current } = useAdminAuth();
  const isSuperAdmin = current?.role === 'super_admin';

  const [name, setName] = useState(user.name);
  const [role, setRole] = useState<AdminRole>(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(): Promise<void> {
    setSaving(true);
    const body: Parameters<typeof usersApi.update>[1] = { name: name.trim(), is_active: isActive };
    if (isSuperAdmin) body.role = role;
    if (password) body.password = password;
    const result = await usersApi.update(user.id, body);
    setSaving(false);
    if (!result.ok) {
      toast.error(result.error.message);
      return;
    }
    toast.success('Usuário atualizado.');
    onSaved();
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Editar ${user.email}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button loading={saving} onClick={() => void submit()}>
            Salvar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Input label="Nome" value={name} onChange={(e) => setName(e.target.value)} />
        <Select
          label="Papel"
          value={role}
          options={ROLE_OPTIONS}
          disabled={!isSuperAdmin}
          hint={!isSuperAdmin ? 'Só um super admin altera papéis.' : undefined}
          onChange={(e) => setRole(e.target.value as AdminRole)}
        />
        <Checkbox label="Conta ativa" checked={isActive} onChange={setIsActive} />
        <Input
          label="Nova senha (opcional)"
          type="password"
          hint="Deixe em branco para manter a senha atual."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
    </Modal>
  );
}

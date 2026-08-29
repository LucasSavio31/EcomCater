'use client';

import { forwardRef, useId } from 'react';
import type { ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { cn } from '@ecom/ui';

interface FieldShellProps {
  label?: ReactNode;
  error?: string;
  hint?: string;
  required?: boolean;
  className?: string;
  htmlFor?: string;
  children: ReactNode;
  describedBy?: string;
}

/** Envelope de rótulo/erro/ajuda reutilizável (mesmo visual do Input do @ecom/ui). */
export function FieldShell({
  label,
  error,
  hint,
  required,
  className,
  htmlFor,
  children,
}: FieldShellProps) {
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {label && (
        <label htmlFor={htmlFor} className="text-sm font-medium text-text">
          {label}
          {required && (
            <span className="ml-0.5 text-danger" aria-hidden="true">
              *
            </span>
          )}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}

const CONTROL_CLASS =
  'min-h-touch w-full rounded-card border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:cursor-not-allowed disabled:opacity-60';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: ReactNode;
  error?: string;
  hint?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, hint, id, className, required, rows = 4, ...rest },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell label={label} error={error} hint={hint} required={required} htmlFor={fieldId} className={className}>
      <textarea
        ref={ref}
        id={fieldId}
        rows={rows}
        required={required}
        aria-invalid={error ? true : undefined}
        className={cn(CONTROL_CLASS, error ? 'border-danger' : 'border-surface-border')}
        {...rest}
      />
    </FieldShell>
  );
});

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: ReactNode;
  error?: string;
  hint?: string;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, hint, id, className, required, options, placeholder, ...rest },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <FieldShell label={label} error={error} hint={hint} required={required} htmlFor={fieldId} className={className}>
      <select
        ref={ref}
        id={fieldId}
        required={required}
        aria-invalid={error ? true : undefined}
        className={cn(CONTROL_CLASS, error ? 'border-danger' : 'border-surface-border')}
        {...rest}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
});

export interface CheckboxProps {
  label: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
  disabled?: boolean;
  id?: string;
}

export function Checkbox({ label, checked, onChange, hint, disabled, id }: CheckboxProps) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={fieldId} className="flex items-center gap-2 text-sm text-text">
        <input
          id={fieldId}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="h-4 w-4 rounded border-surface-border text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        />
        {label}
      </label>
      {hint && <p className="ml-6 text-xs text-text-muted">{hint}</p>}
    </div>
  );
}

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select } from '@/components/ui/select'
import { cn } from '@/lib/utils'

export interface FieldDef {
  name: string
  label: string
  type: 'text' | 'number' | 'date' | 'datetime' | 'textarea' | 'json' | 'select'
  required?: boolean
  options?: { value: string; label: string }[]
  placeholder?: string
}

interface EntityFormProps {
  fields: FieldDef[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  defaultValues?: any
  onSubmit: (data: Record<string, unknown>) => void
  onCancel: () => void
  isLoading?: boolean
  submitLabel?: string
}

export function EntityForm({
  fields,
  defaultValues = {},
  onSubmit,
  onCancel,
  isLoading,
  submitLabel = 'Save',
}: EntityFormProps) {
  function computeValues(defaults: Record<string, unknown>) {
    return fields.reduce<Record<string, unknown>>((acc, field) => {
      const value = defaults[field.name]
      if (field.type === 'json' && value != null) {
        acc[field.name] = typeof value === 'string' ? value : JSON.stringify(value, null, 2)
      } else {
        acc[field.name] = value ?? ''
      }
      return acc
    }, {})
  }

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Record<string, unknown>>({
    defaultValues: computeValues(defaultValues),
  })

  useEffect(() => {
    if (defaultValues) {
      reset(computeValues(defaultValues))
    }
  }, [defaultValues]) // eslint-disable-line react-hooks/exhaustive-deps

  function processSubmit(data: Record<string, unknown>) {
    const processed = { ...data }
    for (const field of fields) {
      if (field.type === 'json' && typeof processed[field.name] === 'string') {
        try {
          processed[field.name] = JSON.parse(processed[field.name] as string)
        } catch {
          // leave as string if invalid JSON
        }
      }
      if (field.type === 'number' && processed[field.name] !== '') {
        processed[field.name] = Number(processed[field.name])
      }
    }
    onSubmit(processed)
  }

  function renderField(field: FieldDef) {
    const hasError = !!errors[field.name]

    switch (field.type) {
      case 'textarea':
      case 'json':
        return (
          <Textarea
            id={field.name}
            {...register(field.name, { required: field.required })}
            placeholder={field.placeholder}
            rows={field.type === 'json' ? 6 : 3}
            className={cn(hasError && 'border-destructive', field.type === 'json' && 'font-mono text-xs')}
          />
        )

      case 'select':
        return (
          <Select
            id={field.name}
            {...register(field.name, { required: field.required })}
            className={cn(hasError && 'border-destructive')}
          >
            <option value="">Select...</option>
            {field.options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </Select>
        )

      case 'number':
        return (
          <Input
            id={field.name}
            type="number"
            {...register(field.name, { required: field.required })}
            placeholder={field.placeholder}
            className={cn(hasError && 'border-destructive')}
          />
        )

      case 'date':
        return (
          <Input
            id={field.name}
            type="date"
            {...register(field.name, { required: field.required })}
            className={cn(hasError && 'border-destructive')}
          />
        )

      case 'datetime':
        return (
          <Input
            id={field.name}
            type="datetime-local"
            {...register(field.name, { required: field.required })}
            className={cn(hasError && 'border-destructive')}
          />
        )

      default:
        return (
          <Input
            id={field.name}
            type="text"
            {...register(field.name, { required: field.required })}
            placeholder={field.placeholder}
            className={cn(hasError && 'border-destructive')}
          />
        )
    }
  }

  return (
    <form onSubmit={handleSubmit(processSubmit)} className="space-y-4">
      {fields.map((field) => (
        <div key={field.name} className="space-y-2">
          <label htmlFor={field.name} className="text-sm font-medium leading-none">
            {field.label}
            {field.required && <span className="text-destructive ml-1">*</span>}
          </label>
          {renderField(field)}
          {errors[field.name] && (
            <p className="text-xs text-destructive">This field is required</p>
          )}
        </div>
      ))}

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : submitLabel}
        </Button>
      </div>
    </form>
  )
}

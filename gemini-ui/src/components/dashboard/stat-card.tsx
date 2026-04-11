import { useNavigate } from '@tanstack/react-router'
import { cn } from '@/lib/utils'

interface StatCardProps {
  title: string
  value: string | number
  icon: React.FC<{ className?: string }>
  loading?: boolean
  href?: string
}

export function StatCard({ title, value, icon: Icon, loading, href }: StatCardProps) {
  const navigate = useNavigate()

  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-6 shadow-sm',
        href && 'cursor-pointer hover:border-primary/50 hover:shadow-md transition-all',
      )}
      data-testid={`stat-card-${title.toLowerCase().replace(/ /g, '-')}`}
      onClick={href ? () => navigate({ to: href as '/' }) : undefined}
      role={href ? 'link' : undefined}
      tabIndex={href ? 0 : undefined}
      onKeyDown={href ? (e) => { if (e.key === 'Enter') navigate({ to: href as '/' }) } : undefined}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <Icon className="h-5 w-5 text-muted-foreground" />
      </div>
      <div className="mt-3">
        {loading ? (
          <div className="h-8 w-16 animate-pulse rounded bg-muted" />
        ) : (
          <p className="text-3xl font-bold tracking-tight" data-testid={`stat-value-${title.toLowerCase().replace(/ /g, '-')}`}>{value}</p>
        )}
      </div>
    </div>
  )
}

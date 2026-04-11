import { useLocation, useNavigate } from '@tanstack/react-router'
import { cn } from '@/lib/utils'
import { ENTITY_GROUPS } from '@/lib/constants'
import {
  LayoutDashboard, FlaskConical, Calendar, MapPin, Users,
  Radio, Cpu, Database, Ruler, Dna, GitBranch,
  Grid3X3, Sprout, Brain, FileCode, ListChecks, Cog,
  FolderOpen, Upload,
} from 'lucide-react'

const iconMap: Record<string, React.FC<{ className?: string }>> = {
  LayoutDashboard, FlaskConical, Calendar, MapPin, Users,
  Radio, Cpu, Database, Ruler, Dna, GitBranch,
  Grid3X3, Sprout, Brain, FileCode, ListChecks, Cog,
  FolderOpen, Upload,
}

export function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <aside className="w-60 h-screen bg-sidebar text-sidebar-foreground border-r border-border flex flex-col overflow-y-auto shrink-0">
      <div className="p-4 border-b border-border">
        <a
          href="/"
          onClick={(e) => { e.preventDefault(); navigate({ to: '/' }) }}
          className="flex items-center gap-2"
        >
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <span className="text-accent font-bold text-sm">G</span>
          </div>
          <span className="font-semibold text-lg tracking-tight">GEMINI</span>
        </a>
      </div>
      <nav className="flex-1 p-3 space-y-4">
        {Object.values(ENTITY_GROUPS).map((group) => (
          <div key={group.label}>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-2 mb-1">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = iconMap[item.icon]
                const isActive = item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path)
                return (
                  <li key={item.path}>
                    <a
                      href={item.path}
                      onClick={(e) => {
                        e.preventDefault()
                        navigate({ to: item.path as '/' })
                      }}
                      className={cn(
                        'flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors',
                        isActive
                          ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                          : 'hover:bg-muted'
                      )}
                    >
                      {Icon && <Icon className="w-4 h-4" />}
                      {item.name}
                    </a>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  )
}

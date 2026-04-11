import * as React from 'react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/*  Context                                                            */
/* ------------------------------------------------------------------ */

interface TabsContextValue {
  value: string
  onValueChange: (value: string) => void
  baseId: string
  registerTrigger: (value: string) => void
  unregisterTrigger: (value: string) => void
  triggerValues: string[]
}

const TabsContext = React.createContext<TabsContextValue | null>(null)

function useTabsContext() {
  const ctx = React.useContext(TabsContext)
  if (!ctx) throw new Error('Tabs compound components must be used within <Tabs>')
  return ctx
}

/* ------------------------------------------------------------------ */
/*  Tabs                                                               */
/* ------------------------------------------------------------------ */

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string
  value?: string
  onValueChange?: (value: string) => void
}

function Tabs({
  defaultValue,
  value: controlledValue,
  onValueChange,
  className,
  children,
  ...props
}: TabsProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue ?? '')
  const [triggerValues, setTriggerValues] = React.useState<string[]>([])
  const value = controlledValue ?? internalValue
  const baseId = React.useId()

  const handleChange = React.useCallback(
    (v: string) => {
      setInternalValue(v)
      onValueChange?.(v)
    },
    [onValueChange],
  )

  const registerTrigger = React.useCallback((val: string) => {
    setTriggerValues((prev) => (prev.includes(val) ? prev : [...prev, val]))
  }, [])

  const unregisterTrigger = React.useCallback((val: string) => {
    setTriggerValues((prev) => prev.filter((v) => v !== val))
  }, [])

  return (
    <TabsContext.Provider value={{ value, onValueChange: handleChange, baseId, registerTrigger, unregisterTrigger, triggerValues }}>
      <div className={cn('', className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

/* ------------------------------------------------------------------ */
/*  TabsList                                                           */
/* ------------------------------------------------------------------ */

function TabsList({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground',
        className,
      )}
      {...props}
    />
  )
}

/* ------------------------------------------------------------------ */
/*  TabsTrigger                                                        */
/* ------------------------------------------------------------------ */

interface TabsTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
}

function TabsTrigger({ value, className, ...props }: TabsTriggerProps) {
  const { value: selected, onValueChange, baseId, registerTrigger, unregisterTrigger, triggerValues } = useTabsContext()
  const isActive = selected === value

  const triggerId = `${baseId}-trigger-${value}`
  const panelId = `${baseId}-panel-${value}`

  React.useEffect(() => {
    registerTrigger(value)
    return () => unregisterTrigger(value)
  }, [value, registerTrigger, unregisterTrigger])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    const idx = triggerValues.indexOf(value)
    if (idx === -1) return

    let nextIdx: number | null = null
    if (e.key === 'ArrowRight') {
      nextIdx = (idx + 1) % triggerValues.length
    } else if (e.key === 'ArrowLeft') {
      nextIdx = (idx - 1 + triggerValues.length) % triggerValues.length
    } else if (e.key === 'Home') {
      nextIdx = 0
    } else if (e.key === 'End') {
      nextIdx = triggerValues.length - 1
    }

    if (nextIdx !== null) {
      e.preventDefault()
      const nextValue = triggerValues[nextIdx]
      onValueChange(nextValue)
      const nextEl = document.getElementById(`${baseId}-trigger-${nextValue}`)
      nextEl?.focus()
    }
  }

  return (
    <button
      id={triggerId}
      role="tab"
      type="button"
      tabIndex={isActive ? 0 : -1}
      aria-selected={isActive}
      aria-controls={panelId}
      data-state={isActive ? 'active' : 'inactive'}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
        isActive
          ? 'bg-background text-foreground shadow-sm'
          : 'hover:bg-background/50 hover:text-foreground',
        className,
      )}
      onClick={() => onValueChange(value)}
      onKeyDown={handleKeyDown}
      {...props}
    />
  )
}

/* ------------------------------------------------------------------ */
/*  TabsContent                                                        */
/* ------------------------------------------------------------------ */

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string
}

function TabsContent({ value, className, children, ...props }: TabsContentProps) {
  const { value: selected, baseId } = useTabsContext()

  if (selected !== value) return null

  const triggerId = `${baseId}-trigger-${value}`
  const panelId = `${baseId}-panel-${value}`

  return (
    <div
      id={panelId}
      role="tabpanel"
      tabIndex={0}
      aria-labelledby={triggerId}
      data-state={selected === value ? 'active' : 'inactive'}
      className={cn(
        'mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }

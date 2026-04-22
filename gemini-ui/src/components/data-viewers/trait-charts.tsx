import { useState, useMemo, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { traitsApi } from '@/api/endpoints/traits'
import type { TraitRecordOutput } from '@/api/types'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Loader2, ChevronDown } from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

function generateColors(count: number): string[] {
  if (count <= 10) {
    return [
      '#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed',
      '#0891b2', '#db2777', '#65a30d', '#ea580c', '#6366f1',
    ].slice(0, count)
  }
  const colors: string[] = []
  for (let i = 0; i < count; i++) {
    const hue = (i * 360 / count) % 360
    colors.push(`hsl(${hue}, 70%, 50%)`)
  }
  return colors
}

const COLORS = [
  '#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed',
  '#0891b2', '#db2777', '#65a30d', '#ea580c', '#6366f1',
]

const NOT_SET = '__all__'

/**
 * Multi-select dropdown with checkboxes. An empty selected set means "All"
 * (no filter applied). Ticking the "All" box clears the selection.
 */
function MultiSelect({
  label,
  options,
  selected,
  onChange,
  width = 'w-44',
  testId,
}: {
  label: string
  options: string[]
  selected: Set<string>
  onChange: (next: Set<string>) => void
  width?: string
  testId?: string
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const isAll = selected.size === 0
  const summary = isAll
    ? `All (${options.length})`
    : selected.size === 1
      ? [...selected][0]
      : `${selected.size} selected`

  function toggle(value: string) {
    const next = new Set(selected)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    onChange(next)
  }

  return (
    <div className="space-y-1">
      <label className="text-xs text-muted-foreground">{label}</label>
      <div ref={containerRef} className="relative">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className={`${width} flex h-10 items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring`}
          data-testid={testId}
        >
          <span className="truncate">{summary}</span>
          <ChevronDown className="w-4 h-4 shrink-0 opacity-60" />
        </button>
        {open && (
          <div className="absolute z-50 mt-1 max-h-64 min-w-full overflow-auto rounded-md border bg-background shadow-lg">
            <label className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-accent border-b">
              <input
                type="checkbox"
                checked={isAll}
                onChange={() => onChange(new Set())}
                className="accent-primary w-4 h-4"
              />
              <span className="font-medium">All ({options.length})</span>
            </label>
            {options.map((opt) => (
              <label key={opt} className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-accent">
                <input
                  type="checkbox"
                  checked={selected.has(opt)}
                  onChange={() => toggle(opt)}
                  className="accent-primary w-4 h-4"
                />
                <span className="truncate">{opt}</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

interface TraitChartsProps {
  traitId: string
  traitName: string
  traitUnits?: string
}

type ChartType = 'histogram' | 'forest' | 'season-trend' | 'site-trend'
type GroupBy = 'none' | 'experiment' | 'season' | 'site'

function extractUnique(records: TraitRecordOutput[], key: keyof TraitRecordOutput): string[] {
  const set = new Set<string>()
  for (const r of records) {
    const v = r[key]
    if (v != null && String(v) !== '') set.add(String(v))
  }
  return [...set].sort()
}

function extractGenotypes(records: TraitRecordOutput[]): string[] {
  const set = new Set<string>()
  for (const r of records) {
    const info = r.record_info as Record<string, unknown> | undefined
    const g = info?.genotype
    if (g != null && String(g).trim() !== '') set.add(String(g).trim())
  }
  return [...set].sort()
}

interface HistogramBin {
  label: string
  binStart: number
  binEnd: number
  [seriesKey: string]: number | string
}

function buildHistogram(
  records: TraitRecordOutput[],
  groupBy: GroupBy,
): { data: HistogramBin[]; seriesKeys: string[] } {
  const values = records.map((r) => r.trait_value!).filter((v) => v != null && !Number.isNaN(v))
  if (values.length === 0) return { data: [], seriesKeys: [] }

  const min = Math.min(...values)
  const max = Math.max(...values)
  const isInteger = values.every((v) => Number.isInteger(v))
  const intRange = Math.round(max) - Math.round(min)

  let binWidth: number
  let binCount: number
  let binBase: number

  if (isInteger && intRange <= 40) {
    // Integer data with a small range: one bin per integer value
    binBase = Math.round(min)
    binCount = intRange + 1
    binWidth = 1
  } else if (isInteger && intRange <= 200) {
    // Integer data with moderate range: round bin width up to a nice integer
    const rawWidth = intRange / 20
    binWidth = Math.max(1, Math.ceil(rawWidth))
    binBase = Math.floor(min)
    binCount = Math.ceil((max - binBase) / binWidth) + 1
  } else {
    // Floating point or very wide integer range
    binCount = 20
    const range = max - min || 1
    binWidth = range / binCount
    binBase = min
  }

  const bins: HistogramBin[] = Array.from({ length: binCount }, (_, i) => {
    const binStart = binBase + i * binWidth
    const binEnd = binStart + binWidth
    const label = isInteger && binWidth === 1
      ? `${Math.round(binStart)}`
      : isInteger
        ? `${Math.round(binStart)}-${Math.round(binEnd - 1)}`
        : `${binStart.toFixed(1)}`
    return { label, binStart, binEnd }
  })

  const seriesSet = new Set<string>()

  for (const r of records) {
    const v = r.trait_value
    if (v == null || Number.isNaN(v)) continue
    let idx = Math.floor((v - binBase) / binWidth)
    if (idx >= binCount) idx = binCount - 1
    if (idx < 0) idx = 0

    let series = 'Count'
    if (groupBy === 'experiment') series = r.experiment_name || 'Unknown'
    else if (groupBy === 'season') series = r.season_name || 'Unknown'
    else if (groupBy === 'site') series = r.site_name || 'Unknown'

    seriesSet.add(series)
    bins[idx][series] = ((bins[idx][series] as number) || 0) + 1
  }

  return { data: bins, seriesKeys: [...seriesSet].sort() }
}

interface GenotypePoint {
  genotype: string
  value: number
  series: string
}

function buildGenotypeData(
  records: TraitRecordOutput[],
  groupBy: GroupBy,
): { points: GenotypePoint[]; genotypes: string[]; seriesKeys: string[]; minVal: number; maxVal: number } {
  const points: GenotypePoint[] = []
  const seriesSet = new Set<string>()
  const genotypeMeans = new Map<string, number[]>()

  for (const r of records) {
    const info = r.record_info as Record<string, unknown> | undefined
    const genotype = info?.genotype ? String(info.genotype).trim() : null
    if (!genotype || r.trait_value == null) continue

    let series = 'All'
    if (groupBy === 'experiment') series = r.experiment_name || 'Unknown'
    else if (groupBy === 'season') series = r.season_name || 'Unknown'
    else if (groupBy === 'site') series = r.site_name || 'Unknown'

    seriesSet.add(series)
    points.push({ genotype, value: r.trait_value, series })
    if (!genotypeMeans.has(genotype)) genotypeMeans.set(genotype, [])
    genotypeMeans.get(genotype)!.push(r.trait_value)
  }

  const genotypes = [...genotypeMeans.entries()]
    .sort((a, b) => {
      const meanA = a[1].reduce((s, v) => s + v, 0) / a[1].length
      const meanB = b[1].reduce((s, v) => s + v, 0) / b[1].length
      return meanB - meanA
    })
    .map(([g]) => g)

  const values = points.map((p) => p.value)
  const minVal = values.length > 0 ? Math.min(...values) : 0
  const maxVal = values.length > 0 ? Math.max(...values) : 1

  return { points, genotypes, seriesKeys: [...seriesSet].sort(), minVal, maxVal }
}

export function TraitCharts({ traitId, traitName, traitUnits }: TraitChartsProps) {
  const [chartType, setChartType] = useState<ChartType>('histogram')
  const [groupBy, setGroupBy] = useState<GroupBy>('none')
  const [filterExperiment, setFilterExperiment] = useState<Set<string>>(new Set())
  const [filterSeason, setFilterSeason] = useState<Set<string>>(new Set())
  const [filterSite, setFilterSite] = useState<Set<string>>(new Set())
  const [filterDataset, setFilterDataset] = useState<Set<string>>(new Set())
  const [filterPopulation, setFilterPopulation] = useState<Set<string>>(new Set())

  const { data: allRecords, isLoading } = useQuery({
    queryKey: ['traitRecords', traitId],
    queryFn: () => traitsApi.getRecords(traitId),
  })

  const experiments = useMemo(() => extractUnique(allRecords ?? [], 'experiment_name'), [allRecords])
  const seasons = useMemo(() => extractUnique(allRecords ?? [], 'season_name'), [allRecords])
  const sites = useMemo(() => extractUnique(allRecords ?? [], 'site_name'), [allRecords])
  const datasets = useMemo(() => extractUnique(allRecords ?? [], 'dataset_name'), [allRecords])
  const populations = useMemo(() => {
    const set = new Set<string>()
    for (const r of allRecords ?? []) {
      const info = r.record_info as Record<string, unknown> | undefined
      const pop = info?.population
      if (pop != null && String(pop).trim() !== '') set.add(String(pop).trim())
    }
    return [...set].sort()
  }, [allRecords])
  const hasGenotypes = useMemo(() => extractGenotypes(allRecords ?? []).length > 0, [allRecords])

  const filtered = useMemo(() => {
    if (!allRecords) return []
    return allRecords.filter((r) => {
      if (filterExperiment.size > 0 && (!r.experiment_name || !filterExperiment.has(r.experiment_name))) return false
      if (filterSeason.size > 0 && (!r.season_name || !filterSeason.has(r.season_name))) return false
      if (filterSite.size > 0 && (!r.site_name || !filterSite.has(r.site_name))) return false
      if (filterDataset.size > 0 && (!r.dataset_name || !filterDataset.has(r.dataset_name))) return false
      if (filterPopulation.size > 0) {
        const info = r.record_info as Record<string, unknown> | undefined
        const pop = info?.population ? String(info.population).trim() : ''
        if (!filterPopulation.has(pop)) return false
      }
      return true
    })
  }, [allRecords, filterExperiment, filterSeason, filterSite, filterDataset, filterPopulation])

  const valueLabel = traitUnits ? `${traitName} (${traitUnits})` : traitName

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 gap-2 text-muted-foreground">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Loading records...</span>
      </div>
    )
  }

  if (!allRecords || allRecords.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No trait records to visualize.</p>
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Chart type</label>
          <Select
            value={chartType}
            onChange={(e) => setChartType(e.target.value as ChartType)}
            className="w-40"
          >
            <option value="histogram">Histogram</option>
            <option value="forest" disabled={!hasGenotypes}>Genotype range</option>
            <option value="season-trend" disabled={!hasGenotypes}>Season trend</option>
            <option value="site-trend" disabled={!hasGenotypes}>Site trend</option>
          </Select>
        </div>

        {chartType !== 'season-trend' && chartType !== 'site-trend' && (
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Group by</label>
            <Select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
              className="w-36"
            >
              <option value="none">None</option>
              <option value="experiment">Experiment</option>
              <option value="season">Season</option>
              <option value="site">Site</option>
            </Select>
          </div>
        )}

        <div className="h-6 w-px bg-border mx-1" />

        <MultiSelect
          label="Experiment"
          options={experiments}
          selected={filterExperiment}
          onChange={setFilterExperiment}
          width="w-44"
          testId="filter-experiment"
        />
        <MultiSelect
          label="Season"
          options={seasons}
          selected={filterSeason}
          onChange={setFilterSeason}
          width="w-40"
          testId="filter-season"
        />
        <MultiSelect
          label="Site"
          options={sites}
          selected={filterSite}
          onChange={setFilterSite}
          width="w-40"
          testId="filter-site"
        />
        <MultiSelect
          label="Dataset"
          options={datasets}
          selected={filterDataset}
          onChange={setFilterDataset}
          width="w-40"
          testId="filter-dataset"
        />
        {populations.length > 0 && (
          <MultiSelect
            label="Population"
            options={populations}
            selected={filterPopulation}
            onChange={setFilterPopulation}
            width="w-44"
            testId="filter-population"
          />
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setFilterExperiment(new Set())
            setFilterSeason(new Set())
            setFilterSite(new Set())
            setFilterDataset(new Set())
            setFilterPopulation(new Set())
          }}
          className="self-end"
        >
          Reset filters
        </Button>
      </div>

      <div className="text-xs text-muted-foreground">
        {filtered.length} of {allRecords.length} records
      </div>

      {/* Chart */}
      {chartType === 'histogram' && <Histogram records={filtered} groupBy={groupBy} valueLabel={valueLabel} />}
      {chartType === 'forest' && <ForestPlot records={filtered} groupBy={groupBy} valueLabel={valueLabel} />}
      {chartType === 'season-trend' && <SeasonTrend records={filtered} valueLabel={valueLabel} />}
      {chartType === 'site-trend' && <SiteTrend records={filtered} valueLabel={valueLabel} />}
    </div>
  )
}

function Histogram({
  records,
  groupBy,
  valueLabel,
}: {
  records: TraitRecordOutput[]
  groupBy: GroupBy
  valueLabel: string
}) {
  const { data, seriesKeys } = useMemo(() => buildHistogram(records, groupBy), [records, groupBy])

  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No data to display.</p>
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data} margin={{ top: 5, right: 20, bottom: 25, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="label"
          label={{ value: valueLabel, position: 'insideBottom', offset: -15 }}
          tick={{ fontSize: 11 }}
        />
        <YAxis
          label={{ value: 'Count', angle: -90, position: 'insideLeft', offset: 10 }}
          tick={{ fontSize: 11 }}
          allowDecimals={false}
        />
        <Tooltip />
        {seriesKeys.length > 1 && <Legend verticalAlign="top" />}
        {seriesKeys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            fill={COLORS[i % COLORS.length]}
            name={key}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

function ForestPlot({
  records,
  groupBy,
  valueLabel,
}: {
  records: TraitRecordOutput[]
  groupBy: GroupBy
  valueLabel: string
}) {
  const { points, genotypes, seriesKeys, minVal, maxVal } = useMemo(
    () => buildGenotypeData(records, groupBy),
    [records, groupBy],
  )
  const [page, setPage] = useState(0)
  const [hoveredGenotype, setHoveredGenotype] = useState<string | null>(null)
  const pageSize = 30
  const totalPages = Math.ceil(genotypes.length / pageSize)
  const pageGenotypes = genotypes.slice(page * pageSize, (page + 1) * pageSize)

  if (genotypes.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No genotype data available. Map a genotype column during import to use this chart.</p>
  }

  const margin = { top: 20, right: 30, bottom: 35, left: 120 }
  const rowHeight = 24
  const chartHeight = margin.top + margin.bottom + pageGenotypes.length * rowHeight
  const chartWidth = 800

  const plotWidth = chartWidth - margin.left - margin.right
  const plotHeight = chartHeight - margin.top - margin.bottom

  const pad = (maxVal - minVal) * 0.05 || 0.5
  const xMin = minVal - pad
  const xMax = maxVal + pad
  const xScale = (v: number) => margin.left + ((v - xMin) / (xMax - xMin)) * plotWidth
  const yScale = (idx: number) => margin.top + idx * rowHeight + rowHeight / 2

  const xTicks: number[] = []
  const tickCount = 6
  for (let i = 0; i <= tickCount; i++) {
    xTicks.push(xMin + (i / tickCount) * (xMax - xMin))
  }

  return (
    <div className="space-y-3">
      {/* Legend */}
      {seriesKeys.length > 1 && (
        <div className="flex items-center gap-4 text-xs">
          {seriesKeys.map((key, i) => (
            <div key={key} className="flex items-center gap-1.5">
              <svg width={10} height={10}>
                <circle cx={5} cy={5} r={4} fill={COLORS[i % COLORS.length]} />
              </svg>
              <span>{key}</span>
            </div>
          ))}
        </div>
      )}

      <div className="overflow-x-auto">
        <svg width={chartWidth} height={chartHeight} className="select-none">
          {/* Grid lines */}
          {xTicks.map((tick) => (
            <line
              key={tick}
              x1={xScale(tick)}
              y1={margin.top}
              x2={xScale(tick)}
              y2={margin.top + plotHeight}
              stroke="#e5e7eb"
              strokeDasharray="3 3"
            />
          ))}

          {/* X-axis ticks */}
          {xTicks.map((tick) => (
            <text
              key={`label-${tick}`}
              x={xScale(tick)}
              y={chartHeight - margin.bottom + 16}
              textAnchor="middle"
              fontSize={10}
              fill="#6b7280"
            >
              {tick.toFixed(1)}
            </text>
          ))}

          {/* X-axis label */}
          <text
            x={margin.left + plotWidth / 2}
            y={chartHeight - 4}
            textAnchor="middle"
            fontSize={11}
            fill="#374151"
          >
            {valueLabel}
          </text>

          {/* Genotype rows */}
          {pageGenotypes.map((genotype, idx) => {
            const y = yScale(idx)
            const genotypePoints = points.filter((p) => p.genotype === genotype)
            const isHovered = hoveredGenotype === genotype

            // Group by series for range lines
            const bySeries = new Map<string, number[]>()
            for (const p of genotypePoints) {
              if (!bySeries.has(p.series)) bySeries.set(p.series, [])
              bySeries.get(p.series)!.push(p.value)
            }

            return (
              <g
                key={genotype}
                onMouseEnter={() => setHoveredGenotype(genotype)}
                onMouseLeave={() => setHoveredGenotype(null)}
              >
                {/* Row background on hover */}
                {isHovered && (
                  <rect
                    x={margin.left}
                    y={y - rowHeight / 2}
                    width={plotWidth}
                    height={rowHeight}
                    fill="#f3f4f6"
                  />
                )}

                {/* Genotype label */}
                <text
                  x={margin.left - 8}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="central"
                  fontSize={11}
                  fill={isHovered ? '#111827' : '#374151'}
                  fontWeight={isHovered ? 600 : 400}
                >
                  {genotype.length > 16 ? genotype.slice(0, 15) + '…' : genotype}
                </text>

                {/* Range lines per series */}
                {seriesKeys.map((series, si) => {
                  const vals = bySeries.get(series)
                  if (!vals || vals.length < 2) return null
                  const sMin = Math.min(...vals)
                  const sMax = Math.max(...vals)
                  const seriesOffset = seriesKeys.length > 1
                    ? (si - (seriesKeys.length - 1) / 2) * 4
                    : 0
                  return (
                    <line
                      key={series}
                      x1={xScale(sMin)}
                      y1={y + seriesOffset}
                      x2={xScale(sMax)}
                      y2={y + seriesOffset}
                      stroke={COLORS[si % COLORS.length]}
                      strokeWidth={1.5}
                      opacity={0.6}
                    />
                  )
                })}

                {/* Individual dots */}
                {genotypePoints.map((p, pi) => {
                  const si = seriesKeys.indexOf(p.series)
                  const seriesOffset = seriesKeys.length > 1
                    ? (si - (seriesKeys.length - 1) / 2) * 4
                    : 0
                  return (
                    <circle
                      key={pi}
                      cx={xScale(p.value)}
                      cy={y + seriesOffset}
                      r={3.5}
                      fill={COLORS[si % COLORS.length]}
                      opacity={0.8}
                      stroke="white"
                      strokeWidth={0.5}
                    >
                      <title>{`${genotype}: ${p.value} (${p.series})`}</title>
                    </circle>
                  )
                })}
              </g>
            )
          })}

          {/* Left border line */}
          <line
            x1={margin.left}
            y1={margin.top}
            x2={margin.left}
            y2={margin.top + plotHeight}
            stroke="#d1d5db"
          />
        </svg>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
          <span className="text-muted-foreground">
            Genotypes {page * pageSize + 1}-{Math.min((page + 1) * pageSize, genotypes.length)} of {genotypes.length}
          </span>
          <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      )}
    </div>
  )
}

/**
 * Per-genotype mean trait value across sites. Mirror of SeasonTrend but
 * keyed on site_name, useful for looking at how the same genotype performs
 * at different locations within the filtered experiment/season slice.
 */
function SiteTrend({
  records,
  valueLabel,
}: {
  records: TraitRecordOutput[]
  valueLabel: string
}) {
  const { chartData, siteOrder, genotypeKeys } = useMemo(() => {
    const genotypeBySite = new Map<string, Map<string, number[]>>()
    const siteSet = new Set<string>()

    for (const r of records) {
      const info = r.record_info as Record<string, unknown> | undefined
      const genotype = info?.genotype ? String(info.genotype).trim() : null
      if (!genotype || r.trait_value == null || !r.site_name) continue

      siteSet.add(r.site_name)
      if (!genotypeBySite.has(genotype)) genotypeBySite.set(genotype, new Map())
      const siteMap = genotypeBySite.get(genotype)!
      if (!siteMap.has(r.site_name)) siteMap.set(r.site_name, [])
      siteMap.get(r.site_name)!.push(r.trait_value)
    }

    const siteOrder = [...siteSet].sort()
    const genotypeKeys = [...genotypeBySite.keys()].sort()

    const chartData = siteOrder.map((site) => {
      const entry: Record<string, unknown> = { site }
      for (const genotype of genotypeKeys) {
        const values = genotypeBySite.get(genotype)?.get(site)
        if (values && values.length > 0) {
          entry[genotype] = values.reduce((a, b) => a + b, 0) / values.length
        }
      }
      return entry
    })

    return { chartData, siteOrder, genotypeKeys }
  }, [records])

  const [hoveredGeno, setHoveredGeno] = useState<string | null>(null)

  if (genotypeKeys.length === 0 || siteOrder.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No genotype data with site information available.</p>
  }

  const colors = generateColors(genotypeKeys.length)

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={450}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 25, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="site"
            tick={{ fontSize: 11 }}
            label={{ value: 'Site', position: 'insideBottom', offset: -15 }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            label={{ value: valueLabel, angle: -90, position: 'insideLeft', offset: 10 }}
          />
          <Tooltip
            isAnimationActive={false}
            content={({ active, label }) => {
              if (!active || !hoveredGeno || !label) return null
              const site = chartData.find((d) => d.site === label)
              const val = site?.[hoveredGeno]
              if (val == null) return null
              return (
                <div className="rounded border bg-background px-2 py-1 text-xs shadow-sm">
                  <p className="font-medium">{hoveredGeno}</p>
                  <p className="text-muted-foreground">{label}: {(val as number).toFixed(2)}</p>
                </div>
              )
            }}
          />
          {genotypeKeys.map((genotype, i) => (
            <Line
              key={genotype}
              type="monotone"
              dataKey={genotype}
              stroke={hoveredGeno && hoveredGeno !== genotype ? colors[i] + '30' : colors[i]}
              strokeWidth={hoveredGeno === genotype ? 2.5 : 1.5}
              dot={{ r: 3, fill: colors[i], strokeWidth: 0 }}
              activeDot={{
                r: 5,
                onMouseEnter: () => setHoveredGeno(genotype),
                onMouseLeave: () => setHoveredGeno(null),
              }}
              connectNulls
              name={genotype}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div className="text-xs text-muted-foreground">
        {genotypeKeys.length} genotypes plotted across {siteOrder.length} site{siteOrder.length === 1 ? '' : 's'}. Hover over a point to identify its genotype.
      </div>
    </div>
  )
}

function SeasonTrend({
  records,
  valueLabel,
}: {
  records: TraitRecordOutput[]
  valueLabel: string
}) {
  const { chartData, seasonOrder, genotypeKeys } = useMemo(() => {
    const genotypeBySeason = new Map<string, Map<string, number[]>>()
    const seasonSet = new Set<string>()

    for (const r of records) {
      const info = r.record_info as Record<string, unknown> | undefined
      const genotype = info?.genotype ? String(info.genotype).trim() : null
      if (!genotype || r.trait_value == null || !r.season_name) continue

      seasonSet.add(r.season_name)
      if (!genotypeBySeason.has(genotype)) genotypeBySeason.set(genotype, new Map())
      const seasonMap = genotypeBySeason.get(genotype)!
      if (!seasonMap.has(r.season_name)) seasonMap.set(r.season_name, [])
      seasonMap.get(r.season_name)!.push(r.trait_value)
    }

    const seasonOrder = [...seasonSet].sort()
    const genotypeKeys = [...genotypeBySeason.keys()].sort()

    const chartData = seasonOrder.map((season) => {
      const entry: Record<string, unknown> = { season }
      for (const genotype of genotypeKeys) {
        const values = genotypeBySeason.get(genotype)?.get(season)
        if (values && values.length > 0) {
          entry[genotype] = values.reduce((a, b) => a + b, 0) / values.length
        }
      }
      return entry
    })

    return { chartData, seasonOrder, genotypeKeys }
  }, [records])

  if (genotypeKeys.length === 0 || seasonOrder.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No genotype data with season information available.</p>
  }

  const colors = generateColors(genotypeKeys.length)
  const [hoveredGeno, setHoveredGeno] = useState<string | null>(null)

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={450}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 25, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="season"
            tick={{ fontSize: 11 }}
            label={{ value: 'Season', position: 'insideBottom', offset: -15 }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            label={{ value: valueLabel, angle: -90, position: 'insideLeft', offset: 10 }}
          />
          <Tooltip
            isAnimationActive={false}
            content={({ active, label }) => {
              if (!active || !hoveredGeno || !label) return null
              const season = chartData.find((d) => d.season === label)
              const val = season?.[hoveredGeno]
              if (val == null) return null
              return (
                <div className="rounded border bg-background px-2 py-1 text-xs shadow-sm">
                  <p className="font-medium">{hoveredGeno}</p>
                  <p className="text-muted-foreground">{label}: {(val as number).toFixed(2)}</p>
                </div>
              )
            }}
          />
          {genotypeKeys.map((genotype, i) => (
            <Line
              key={genotype}
              type="monotone"
              dataKey={genotype}
              stroke={hoveredGeno && hoveredGeno !== genotype ? colors[i] + '30' : colors[i]}
              strokeWidth={hoveredGeno === genotype ? 2.5 : 1.5}
              dot={{ r: 3, fill: colors[i], strokeWidth: 0 }}
              activeDot={{
                r: 5,
                onMouseEnter: () => setHoveredGeno(genotype),
                onMouseLeave: () => setHoveredGeno(null),
              }}
              connectNulls
              name={genotype}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div className="text-xs text-muted-foreground">
        {genotypeKeys.length} genotypes plotted. Hover over a point to identify its genotype.
      </div>
    </div>
  )
}

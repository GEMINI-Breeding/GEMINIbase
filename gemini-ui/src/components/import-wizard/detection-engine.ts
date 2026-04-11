import type { FileWithPath } from '@/components/upload/dropzone'

export interface DetectedFileGroup {
  date: string | null
  folder: string
  files: FileWithPath[]
  fileCount: number
  totalSize: number
}

export interface DetectedCsv {
  file: FileWithPath
  name: string
  headers: string[]
  sampleRows: string[][]
  category: 'field_design' | 'gcp_locations' | 'trait_data' | 'sensor_data' | 'unknown'
}

export interface DetectionResult {
  fileGroups: DetectedFileGroup[]
  csvFiles: DetectedCsv[]
  totalFiles: number
  totalSize: number
  detectedDates: string[]
  suggestedDataFormat: string
  suggestedSensorType: string | null
  suggestedPlatform: string | null
  suggestedExperimentName: string | null
  suggestedSiteName: string | null
  dataCategories: DataCategory[]
}

export type DataCategory = 'drone_imagery' | 'csv_tabular' | 'genomic' | 'thermal' | 'elevation' | 'mixed'

const DATE_PATTERN = /(\d{4})-(\d{2})-(\d{2})/
const DJI_PATTERN = /DJI_\d{4}/i
const AMIGA_PATTERN = /Amiga/i

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'tif', 'tiff'])
const GENOMIC_EXTENSIONS = new Set(['vcf', 'hapmap', 'hmp', 'ped', 'map', 'bed', 'bim', 'fam'])
const CSV_EXTENSIONS = new Set(['csv', 'tsv', 'txt'])
const SPREADSHEET_EXTENSIONS = new Set(['xlsx', 'xls', 'ods'])
const THERMAL_EXTENSIONS = new Set(['fff', 'seq'])

function getExtension(filename: string): string {
  return filename.split('.').pop()?.toLowerCase() || ''
}

function extractDateFromPath(path: string): string | null {
  const match = path.match(DATE_PATTERN)
  return match ? `${match[1]}-${match[2]}-${match[3]}` : null
}

function inferSiteName(paths: string[]): string | null {
  for (const p of paths) {
    const parts = p.split('/')
    for (const part of parts) {
      const cleaned = part.replace(DATE_PATTERN, '').replace(/^-|-$/g, '').trim()
      if (cleaned.length > 2 && !cleaned.match(/^\d+$/) && !cleaned.match(/DJI|MEDIA|DCIM/i)) {
        return cleaned
      }
    }
  }
  return null
}

function categorizeCSV(headers: string[]): DetectedCsv['category'] {
  const lower = headers.map((h) => h.toLowerCase())
  if (lower.some((h) => h.includes('plot') && (h.includes('row') || h.includes('col') || h.includes('range')))) {
    return 'field_design'
  }
  if (lower.some((h) => h.includes('gcp') || h.includes('ground_control') || (h.includes('lat') && lower.some((l) => l.includes('lon'))))) {
    return 'gcp_locations'
  }
  if (lower.some((h) => h.includes('trait') || h.includes('measurement') || h.includes('phenotype'))) {
    return 'trait_data'
  }
  if (lower.some((h) => h.includes('sensor') || h.includes('temperature') || h.includes('humidity'))) {
    return 'sensor_data'
  }
  return 'unknown'
}

function splitCSVLine(line: string, delimiter: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  for (const char of line) {
    if (char === '"') { inQuotes = !inQuotes; continue }
    if (char === delimiter && !inQuotes) { result.push(current.trim()); current = ''; continue }
    current += char
  }
  result.push(current.trim())
  return result
}

async function parseCSVPreview(file: FileWithPath): Promise<DetectedCsv> {
  const text = await file.slice(0, 8192).text()
  const lines = text.split('\n').filter((l) => l.trim())
  const delimiter = lines[0]?.includes('\t') ? '\t' : ','
  const headers = lines[0] ? splitCSVLine(lines[0], delimiter) : []
  const sampleRows = lines.slice(1, 4).map((line) => splitCSVLine(line, delimiter))

  return {
    file,
    name: file.name,
    headers,
    sampleRows,
    category: categorizeCSV(headers),
  }
}

export async function detectFiles(files: FileWithPath[]): Promise<DetectionResult> {
  const groups = new Map<string, FileWithPath[]>()
  const csvFiles: FileWithPath[] = []
  const dates = new Set<string>()
  let hasDJI = false
  let hasAmiga = false
  let hasImages = false
  let hasGenomic = false
  let hasThermal = false
  let hasSpreadsheet = false

  for (const file of files) {
    const ext = getExtension(file.name)
    const path = file.path || file.name

    // Extract date
    const date = extractDateFromPath(path)
    if (date) dates.add(date)

    // Group by parent folder
    const parts = path.split('/')
    const folder = parts.length > 1 ? parts.slice(0, -1).join('/') : '.'
    if (!groups.has(folder)) groups.set(folder, [])
    groups.get(folder)!.push(file)

    // Detect patterns
    if (DJI_PATTERN.test(file.name)) hasDJI = true
    if (AMIGA_PATTERN.test(path)) hasAmiga = true
    if (IMAGE_EXTENSIONS.has(ext)) hasImages = true
    if (GENOMIC_EXTENSIONS.has(ext)) hasGenomic = true
    if (THERMAL_EXTENSIONS.has(ext) || (ext === 'tiff' && path.toLowerCase().includes('flir'))) hasThermal = true
    if (CSV_EXTENSIONS.has(ext)) csvFiles.push(file)
    if (SPREADSHEET_EXTENSIONS.has(ext)) hasSpreadsheet = true
  }

  // Parse CSV previews
  const parsedCsvs = await Promise.all(csvFiles.map(parseCSVPreview))

  // Build file groups
  const fileGroups: DetectedFileGroup[] = []
  for (const [folder, folderFiles] of groups) {
    const date = extractDateFromPath(folder)
    fileGroups.push({
      date,
      folder,
      files: folderFiles,
      fileCount: folderFiles.length,
      totalSize: folderFiles.reduce((sum, f) => sum + f.size, 0),
    })
  }
  fileGroups.sort((a, b) => (a.date || '').localeCompare(b.date || ''))

  // Determine categories
  const categories: DataCategory[] = []
  if (hasDJI || (hasImages && dates.size > 0)) categories.push('drone_imagery')
  if (hasGenomic) categories.push('genomic')
  if (hasThermal) categories.push('thermal')
  if (parsedCsvs.length > 0 && !hasImages) categories.push('csv_tabular')
  if (hasSpreadsheet) categories.push('csv_tabular')
  if (categories.length === 0) categories.push('mixed')

  // Infer suggestions
  const allPaths = files.map((f) => f.path || f.name)
  const suggestedSiteName = inferSiteName(allPaths)

  let suggestedSensorType: string | null = null
  let suggestedPlatform: string | null = null
  let suggestedDataFormat: string

  if (hasDJI) {
    suggestedSensorType = 'RGB Camera'
    suggestedPlatform = 'DJI Drone'
    suggestedDataFormat = 'JPEG'
  } else if (hasAmiga) {
    suggestedSensorType = 'Multi-sensor'
    suggestedPlatform = 'Amiga Robot'
    suggestedDataFormat = 'Mixed'
  } else if (hasGenomic) {
    const ext = files.find((f) => GENOMIC_EXTENSIONS.has(getExtension(f.name)))
    suggestedDataFormat = ext ? getExtension(ext.name).toUpperCase() : 'VCF'
  } else if (hasImages) {
    suggestedSensorType = 'Camera'
    suggestedDataFormat = 'JPEG'
  } else if (hasSpreadsheet) {
    suggestedDataFormat = 'XLSX'
  } else if (parsedCsvs.length > 0) {
    suggestedDataFormat = 'CSV'
  } else {
    suggestedDataFormat = 'Unknown'
  }

  // Try to infer experiment name from top-level folder
  const topFolders = [...new Set(files.map((f) => (f.path || f.name).split('/')[0]))]
  const suggestedExperimentName = topFolders.length === 1 && topFolders[0] !== files[0]?.name
    ? topFolders[0].replace(DATE_PATTERN, '').replace(/^-|-$/g, '').trim() || null
    : null

  return {
    fileGroups,
    csvFiles: parsedCsvs,
    totalFiles: files.length,
    totalSize: files.reduce((sum, f) => sum + f.size, 0),
    detectedDates: [...dates].sort(),
    suggestedDataFormat,
    suggestedSensorType,
    suggestedPlatform,
    suggestedExperimentName,
    suggestedSiteName,
    dataCategories: categories,
  }
}

/** Returns true if the detected data categories involve sensor/platform data */
export function needsSensorFields(categories: DataCategory[]): boolean {
  const sensorCategories: DataCategory[] = ['drone_imagery', 'thermal', 'elevation']
  return categories.some((c) => sensorCategories.includes(c))
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

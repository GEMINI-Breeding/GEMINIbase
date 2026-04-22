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
  category: 'field_design' | 'gcp_locations' | 'trait_data' | 'sensor_data' | 'genomic_matrix' | 'unknown'
}

/**
 * Identifies the layout of a genomic-matrix-shaped spreadsheet/CSV: which
 * columns carry variant metadata (SNP name, chromosome, position, alleles)
 * and which carry per-sample genotype calls. Populated by
 * `inspectMatrixShape` when the detection engine thinks a file is a HapMap-
 * style matrix; surfaced to the wizard so the ingest step can parse without
 * asking the user to map 300+ columns by hand.
 */
export interface GenomicMatrixShape {
  format: 'matrix' | 'hapmap' | 'vcf' | 'plink'
  /** Zero-based index of the header row; 0 unless a banner row precedes it. */
  headerRowIndex: number
  /** Indices of columns that hold variant metadata (skipped when ingesting calls). */
  metadataColumnIndices: number[]
  /** Indices of columns that hold per-sample genotype calls. */
  sampleColumnIndices: number[]
  /** Resolved header text for each sample column (canonical accession candidate). */
  sampleHeaders: string[]
  variantNameColumnIndex: number | null
  chromosomeColumnIndex: number | null
  positionColumnIndex: number | null
  allelesColumnIndex: number | null
  designSequenceColumnIndex: number | null
  /** True when we're confident; false when we guessed a fallback and the wizard should prompt. */
  confident: boolean
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
  /** Populated only when a genomic matrix / HapMap / VCF file was detected. */
  genomicShape?: GenomicMatrixShape | null
  /** The single file that carries genomic data (matrix xlsx, .hmp, .vcf). */
  genomicFile?: FileWithPath | null
}

export type DataCategory = 'drone_imagery' | 'csv_tabular' | 'genomic' | 'thermal' | 'elevation' | 'mixed'

const DATE_PATTERN = /(\d{4})-(\d{2})-(\d{2})/
const DJI_PATTERN = /DJI_\d{4}/i
const AMIGA_PATTERN = /Amiga/i

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'tif', 'tiff'])
const GENOMIC_EXTENSIONS = new Set(['vcf', 'hapmap', 'hmp', 'ped', 'map', 'bed', 'bim', 'fam'])
const HAPMAP_EXTENSIONS = new Set(['hmp', 'hapmap'])
const VCF_EXTENSIONS = new Set(['vcf'])
const PLINK_EXTENSIONS = new Set(['ped', 'map', 'bed', 'bim', 'fam'])
const CSV_EXTENSIONS = new Set(['csv', 'tsv', 'txt'])
const SPREADSHEET_EXTENSIONS = new Set(['xlsx', 'xls', 'ods'])
const THERMAL_EXTENSIONS = new Set(['fff', 'seq'])

const VARIANT_NAME_HEADER_RE = /^(snp[\s_]?name|rs#?|marker|variant[_\s]?name|id)$/i
const CHROMOSOME_HEADER_RE = /^(chr(om(osome)?)?|#chrom)$/i
const POSITION_HEADER_RE = /^(pos(ition)?|bp|cm|map[\s_]?pos)$/i
const ALLELES_HEADER_RE = /^(alleles?|snp[_\s]?allele|ref[/\\]?alt)$/i
const DESIGN_SEQ_HEADER_RE = /^(design[_\s]?seq(uence)?|flanking[_\s]?seq(uence)?|sequence)$/i
/** Two-letter IUPAC genotype calls like TT, CC, AG, NN, or numeric 0/1/2. */
const GENOTYPE_CALL_RE = /^([ACGTNacgtn-]{1,2}|[012]|NA|-)$/

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

function categorizeCSV(headers: string[], sampleRows: string[][] = []): DetectedCsv['category'] {
  // Check for genomic matrix shape first — if we see variant metadata
  // headers plus a field of 2-char genotype calls in the sample rows,
  // this is definitively NOT trait_data even though it's row-oriented.
  if (looksLikeGenomicMatrix(headers, sampleRows)) {
    return 'genomic_matrix'
  }
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

/**
 * Heuristic: a matrix is genomic if it has at least one variant-metadata
 * header (SNP Name / Chr / Pos / Alleles) AND the majority of cells in the
 * non-metadata columns of the first few sample rows are short genotype-call
 * tokens (TT/CC/AG/NN/0/1/2/etc).
 */
function looksLikeGenomicMatrix(headers: string[], sampleRows: string[][]): boolean {
  if (headers.length < 4 || sampleRows.length === 0) return false

  const metadataIndices = new Set<number>()
  let hasVariantName = false
  headers.forEach((h, i) => {
    const trimmed = (h || '').trim()
    if (VARIANT_NAME_HEADER_RE.test(trimmed)) { metadataIndices.add(i); hasVariantName = true }
    else if (CHROMOSOME_HEADER_RE.test(trimmed)) metadataIndices.add(i)
    else if (POSITION_HEADER_RE.test(trimmed)) metadataIndices.add(i)
    else if (ALLELES_HEADER_RE.test(trimmed)) metadataIndices.add(i)
    else if (DESIGN_SEQ_HEADER_RE.test(trimmed)) metadataIndices.add(i)
  })

  if (!hasVariantName) return false

  const sampleIndices = headers
    .map((_, i) => i)
    .filter((i) => !metadataIndices.has(i))

  if (sampleIndices.length < 3) return false

  // Look at up to the first 3 data rows × sample columns: what fraction are
  // genotype-call-shaped?
  let total = 0
  let matches = 0
  for (const row of sampleRows.slice(0, 3)) {
    for (const idx of sampleIndices) {
      const cell = (row[idx] ?? '').toString().trim()
      if (!cell) continue
      total++
      if (GENOTYPE_CALL_RE.test(cell)) matches++
    }
  }
  if (total === 0) return false
  return matches / total >= 0.6
}

/**
 * Build a GenomicMatrixShape from a set of headers once we've decided the
 * file is a genomic matrix. Returns null if no variant-name column is
 * present (shouldn't happen after looksLikeGenomicMatrix passes, but guard
 * anyway).
 */
export function buildMatrixShape(
  headers: string[],
  format: GenomicMatrixShape['format'] = 'matrix',
  headerRowIndex = 0,
): GenomicMatrixShape | null {
  let variantNameColumnIndex: number | null = null
  let chromosomeColumnIndex: number | null = null
  let positionColumnIndex: number | null = null
  let allelesColumnIndex: number | null = null
  let designSequenceColumnIndex: number | null = null
  const metadataColumnIndices: number[] = []

  headers.forEach((h, i) => {
    const trimmed = (h || '').trim()
    if (VARIANT_NAME_HEADER_RE.test(trimmed)) {
      if (variantNameColumnIndex === null) variantNameColumnIndex = i
      metadataColumnIndices.push(i)
    } else if (CHROMOSOME_HEADER_RE.test(trimmed)) {
      chromosomeColumnIndex = i
      metadataColumnIndices.push(i)
    } else if (POSITION_HEADER_RE.test(trimmed)) {
      positionColumnIndex = i
      metadataColumnIndices.push(i)
    } else if (ALLELES_HEADER_RE.test(trimmed)) {
      allelesColumnIndex = i
      metadataColumnIndices.push(i)
    } else if (DESIGN_SEQ_HEADER_RE.test(trimmed)) {
      designSequenceColumnIndex = i
      metadataColumnIndices.push(i)
    }
  })

  if (variantNameColumnIndex === null) return null

  const metaSet = new Set(metadataColumnIndices)
  const sampleColumnIndices: number[] = []
  const sampleHeaders: string[] = []
  headers.forEach((h, i) => {
    if (metaSet.has(i)) return
    const trimmed = (h || '').trim()
    if (!trimmed) return
    sampleColumnIndices.push(i)
    sampleHeaders.push(trimmed)
  })

  return {
    format,
    headerRowIndex,
    metadataColumnIndices,
    sampleColumnIndices,
    sampleHeaders,
    variantNameColumnIndex,
    chromosomeColumnIndex,
    positionColumnIndex,
    allelesColumnIndex,
    designSequenceColumnIndex,
    confident: true,
  }
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
    category: categorizeCSV(headers, sampleRows),
  }
}

/**
 * Lightweight peek at the first sheet of an xlsx/xls/ods: returns the
 * header row and up to 3 sample rows from the data area. Uses the xlsx
 * library's sheet_to_json with {header: 1} (arrays of arrays) so we don't
 * pay for full parsing of a 32k-row workbook when all we need is the top.
 */
async function peekSpreadsheet(
  file: FileWithPath,
): Promise<{ headers: string[]; sampleRows: string[][]; headerRowIndex: number } | null> {
  try {
    const XLSX = await import('xlsx')
    const buffer = await file.arrayBuffer()
    const workbook = XLSX.read(buffer, { type: 'array', sheetRows: 8 })
    const sheetName = workbook.SheetNames[0]
    if (!sheetName) return null
    const sheet = workbook.Sheets[sheetName]
    if (!sheet) return null
    const raw = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' })
    // Some supplements start with a banner/description row (one populated
    // cell, rest empty). Skip rows until we find one where ≥4 cells are
    // non-empty — that's almost certainly the real header row.
    let headerRowIndex = 0
    for (let i = 0; i < Math.min(raw.length, 5); i++) {
      const row = raw[i] ?? []
      const populated = row.filter((c) => c !== '' && c != null).length
      if (populated >= 4) { headerRowIndex = i; break }
    }
    const headerRow = (raw[headerRowIndex] ?? []).map((c) => String(c ?? '').trim())
    const sampleRows = raw
      .slice(headerRowIndex + 1, headerRowIndex + 4)
      .map((r) => (r ?? []).map((c) => String(c ?? '')))
    return { headers: headerRow, sampleRows, headerRowIndex }
  } catch {
    return null
  }
}

/** Peek the first few lines of a text genomic file (HapMap / VCF). */
async function peekTextHead(file: FileWithPath, bytes = 16384): Promise<string> {
  return file.slice(0, bytes).text()
}

/**
 * Parse the #CHROM line of a VCF preview to extract sample headers.
 * Returns null if the preview doesn't contain a #CHROM line (file might
 * not be VCF, or bytes budget too small).
 */
function inspectVcfPreview(text: string): GenomicMatrixShape | null {
  const lines = text.split('\n')
  const headerLine = lines.find((l) => l.startsWith('#CHROM'))
  if (!headerLine) return null
  const cols = headerLine.replace(/^#/, '').split('\t')
  // VCF fixed columns: CHROM POS ID REF ALT QUAL FILTER INFO FORMAT
  const fixedCount = 9
  if (cols.length <= fixedCount) return null
  const sampleHeaders = cols.slice(fixedCount).map((s) => s.trim()).filter(Boolean)
  if (sampleHeaders.length === 0) return null
  const metadataColumnIndices = Array.from({ length: fixedCount }, (_, i) => i)
  const sampleColumnIndices = Array.from({ length: sampleHeaders.length }, (_, i) => fixedCount + i)
  return {
    format: 'vcf',
    headerRowIndex: 0,
    metadataColumnIndices,
    sampleColumnIndices,
    sampleHeaders,
    variantNameColumnIndex: 2, // ID column
    chromosomeColumnIndex: 0,
    positionColumnIndex: 1,
    allelesColumnIndex: 3, // REF; ALT is col 4 — parsers handle both
    designSequenceColumnIndex: null,
    confident: true,
  }
}

/**
 * Inspect the header line of a HapMap preview. HapMap format is a TSV with
 * 11 fixed columns (rs#, alleles, chrom, pos, strand, assembly#, center,
 * protLSID, assayLSID, panelLSID, QCcode) followed by sample columns.
 */
function inspectHapmapPreview(text: string): GenomicMatrixShape | null {
  const lines = text.split('\n').filter((l) => l.trim())
  if (lines.length === 0) return null
  const headers = lines[0].split('\t').map((s) => s.trim())
  if (headers.length <= 11) return null
  if (!/^rs#?$/i.test(headers[0])) return null
  const metadataColumnIndices = Array.from({ length: 11 }, (_, i) => i)
  const sampleHeaders = headers.slice(11)
  const sampleColumnIndices = Array.from({ length: sampleHeaders.length }, (_, i) => 11 + i)
  return {
    format: 'hapmap',
    headerRowIndex: 0,
    metadataColumnIndices,
    sampleColumnIndices,
    sampleHeaders,
    variantNameColumnIndex: 0,
    chromosomeColumnIndex: 2,
    positionColumnIndex: 3,
    allelesColumnIndex: 1,
    designSequenceColumnIndex: null,
    confident: true,
  }
}

export async function detectFiles(files: FileWithPath[]): Promise<DetectionResult> {
  const groups = new Map<string, FileWithPath[]>()
  const csvFiles: FileWithPath[] = []
  const spreadsheetFiles: FileWithPath[] = []
  const dates = new Set<string>()
  let hasDJI = false
  let hasAmiga = false
  let hasImages = false
  let hasGenomicExt = false
  let hasPlinkExt = false
  let hasHapmapExt = false
  let hasVcfExt = false
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
    if (GENOMIC_EXTENSIONS.has(ext)) hasGenomicExt = true
    if (PLINK_EXTENSIONS.has(ext)) hasPlinkExt = true
    if (HAPMAP_EXTENSIONS.has(ext)) hasHapmapExt = true
    if (VCF_EXTENSIONS.has(ext)) hasVcfExt = true
    if (THERMAL_EXTENSIONS.has(ext) || (ext === 'tiff' && path.toLowerCase().includes('flir'))) hasThermal = true
    if (CSV_EXTENSIONS.has(ext)) csvFiles.push(file)
    if (SPREADSHEET_EXTENSIONS.has(ext)) {
      hasSpreadsheet = true
      spreadsheetFiles.push(file)
    }
  }

  // Parse CSV previews
  const parsedCsvs = await Promise.all(csvFiles.map(parseCSVPreview))

  // --- Genomic content inspection --------------------------------------
  //
  // Extension alone is unreliable here: .xlsx can hold either a trait table
  // or a HapMap-style SNP matrix, and we need to tell them apart before
  // deciding whether to route to the trait wizard. Peek the first sheet of
  // each xlsx, and peek the first KB of .hmp/.vcf files, to decide.
  let genomicShape: GenomicMatrixShape | null = null
  let genomicFile: FileWithPath | null = null
  let matrixXlsxFile: FileWithPath | null = null

  for (const sheetFile of spreadsheetFiles) {
    const peek = await peekSpreadsheet(sheetFile)
    if (!peek) continue
    if (looksLikeGenomicMatrix(peek.headers, peek.sampleRows)) {
      const shape = buildMatrixShape(peek.headers, 'matrix', peek.headerRowIndex)
      if (shape) {
        genomicShape = shape
        genomicFile = sheetFile
        matrixXlsxFile = sheetFile
        break
      }
    }
  }

  // HapMap text files — prefer content-based shape even when extension already gave us a hint.
  if (!genomicShape && hasHapmapExt) {
    const hapmapFile = files.find((f) => HAPMAP_EXTENSIONS.has(getExtension(f.name)))
    if (hapmapFile) {
      const head = await peekTextHead(hapmapFile)
      const shape = inspectHapmapPreview(head)
      if (shape) {
        genomicShape = shape
        genomicFile = hapmapFile
      }
    }
  }

  // VCF text files
  if (!genomicShape && hasVcfExt) {
    const vcfFile = files.find((f) => VCF_EXTENSIONS.has(getExtension(f.name)))
    if (vcfFile) {
      const head = await peekTextHead(vcfFile)
      const shape = inspectVcfPreview(head)
      if (shape) {
        genomicShape = shape
        genomicFile = vcfFile
      }
    }
  }

  // PLINK: we detect the extension but don't parse it. Surface the
  // category so the wizard can route to a "not yet supported" screen.
  if (!genomicShape && hasPlinkExt) {
    const plinkFile = files.find((f) => PLINK_EXTENSIONS.has(getExtension(f.name)))
    if (plinkFile) {
      genomicFile = plinkFile
      genomicShape = {
        format: 'plink',
        headerRowIndex: 0,
        metadataColumnIndices: [],
        sampleColumnIndices: [],
        sampleHeaders: [],
        variantNameColumnIndex: null,
        chromosomeColumnIndex: null,
        positionColumnIndex: null,
        allelesColumnIndex: null,
        designSequenceColumnIndex: null,
        confident: false,
      }
    }
  }

  // CSVs with genomic-matrix shape get reclassified here so the wizard
  // sees them as genomic rather than as csv_tabular.
  if (!genomicShape) {
    const matrixCsv = parsedCsvs.find((c) => c.category === 'genomic_matrix')
    if (matrixCsv) {
      const shape = buildMatrixShape(matrixCsv.headers, 'matrix', 0)
      if (shape) {
        genomicShape = shape
        genomicFile = matrixCsv.file
      }
    }
  }

  const hasGenomic = hasGenomicExt || genomicShape !== null

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

  // Determine categories. If we positively identified a genomic shape in an
  // xlsx, suppress the csv_tabular tag for that file — otherwise the wizard
  // happily feeds a 32k-row SNP matrix into the trait mapper.
  const categories: DataCategory[] = []
  if (hasDJI || (hasImages && dates.size > 0)) categories.push('drone_imagery')
  if (hasGenomic) categories.push('genomic')
  if (hasThermal) categories.push('thermal')
  const suppressTabular = matrixXlsxFile !== null &&
    spreadsheetFiles.length === 1 &&
    parsedCsvs.length === 0
  if (!suppressTabular) {
    if (parsedCsvs.some((c) => c.category !== 'genomic_matrix') && !hasImages) {
      categories.push('csv_tabular')
    }
    if (hasSpreadsheet && !matrixXlsxFile) categories.push('csv_tabular')
  }
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
    if (genomicShape?.format === 'hapmap') suggestedDataFormat = 'HapMap'
    else if (genomicShape?.format === 'vcf') suggestedDataFormat = 'VCF'
    else if (genomicShape?.format === 'plink') suggestedDataFormat = 'PLINK'
    else if (genomicShape?.format === 'matrix') suggestedDataFormat = 'Genomic Matrix'
    else {
      const ext = files.find((f) => GENOMIC_EXTENSIONS.has(getExtension(f.name)))
      suggestedDataFormat = ext ? getExtension(ext.name).toUpperCase() : 'Genomic'
    }
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
    genomicShape,
    genomicFile,
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

/**
 * Generate a small HapMap-style genomic matrix xlsx for the genomic
 * import wizard e2e test. Layout mirrors the cowpea MAGIC supplement:
 *   rows = SNP variants, cols = variant metadata + per-sample calls.
 */
import * as XLSX from 'xlsx'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export interface GenomicMatrixFixture {
  path: string
  sampleHeaders: string[]
  variantCount: number
}

// Use a run-unique token in both sample and variant names so repeated test
// runs don't see leftover data and skip the "unresolved" branch we want to
// exercise. The token also makes DB cleanup by substring straightforward.
const FIXTURE_RUN_TOKEN = `e2efix${Date.now().toString(36)}`

const SAMPLE_HEADERS = [
  `SAMPLE_A_${FIXTURE_RUN_TOKEN}`,
  `SAMPLE_B_${FIXTURE_RUN_TOKEN}`,
  `SAMPLE_C_${FIXTURE_RUN_TOKEN}`,
  `SAMPLE_D_${FIXTURE_RUN_TOKEN}`,
]

export const GENOMIC_FIXTURE_RUN_TOKEN = FIXTURE_RUN_TOKEN

// 10 variants × 4 samples. Cells use the HapMap-style two-letter IUPAC
// genotype calls so the detection heuristic recognizes the layout. Sample
// headers and variant names both embed FIXTURE_RUN_TOKEN so a re-run of
// the test exercises the "unresolved → auto-create" branch cleanly.
const [SA, SB, SC, SD] = SAMPLE_HEADERS
const VARIANT_ROWS: Array<Record<string, string | number>> = [
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_001`, 'SNP allele': 'T/C', Chr: 1, cM: 0.0, [SA]: 'TT', [SB]: 'CC', [SC]: 'TT', [SD]: 'TC' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_002`, 'SNP allele': 'A/G', Chr: 1, cM: 1.2, [SA]: 'AA', [SB]: 'AG', [SC]: 'GG', [SD]: 'AA' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_003`, 'SNP allele': 'G/C', Chr: 2, cM: 0.5, [SA]: 'GG', [SB]: 'CC', [SC]: 'GC', [SD]: 'GG' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_004`, 'SNP allele': 'T/A', Chr: 2, cM: 2.1, [SA]: 'TT', [SB]: 'TT', [SC]: 'AA', [SD]: 'TA' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_005`, 'SNP allele': 'C/T', Chr: 3, cM: 0.3, [SA]: 'CC', [SB]: 'CT', [SC]: 'TT', [SD]: 'CC' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_006`, 'SNP allele': 'G/A', Chr: 3, cM: 1.8, [SA]: 'GA', [SB]: 'GG', [SC]: 'AA', [SD]: 'GA' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_007`, 'SNP allele': 'A/T', Chr: 4, cM: 0.7, [SA]: 'AA', [SB]: 'TT', [SC]: 'AT', [SD]: 'AA' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_008`, 'SNP allele': 'C/G', Chr: 4, cM: 2.5, [SA]: 'GG', [SB]: 'CC', [SC]: 'CG', [SD]: 'CC' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_009`, 'SNP allele': 'T/G', Chr: 5, cM: 0.1, [SA]: 'TT', [SB]: 'GG', [SC]: 'TG', [SD]: 'TT' },
  { 'SNP Name': `${FIXTURE_RUN_TOKEN}_snp_010`, 'SNP allele': 'A/C', Chr: 5, cM: 3.3, [SA]: 'AA', [SB]: 'CC', [SC]: 'AC', [SD]: 'AA' },
]

export const GENOMIC_MATRIX_FIXTURE_PATH = path.join(
  __dirname,
  'genomic_matrix_sample.xlsx',
)

export const GENOMIC_MATRIX_FIXTURE: GenomicMatrixFixture = {
  path: GENOMIC_MATRIX_FIXTURE_PATH,
  sampleHeaders: SAMPLE_HEADERS,
  variantCount: VARIANT_ROWS.length,
}

export function generateGenomicMatrixFixture(): string {
  const workbook = XLSX.utils.book_new()
  const sheet = XLSX.utils.json_to_sheet(VARIANT_ROWS, {
    header: ['SNP Name', 'SNP allele', 'Chr', 'cM', ...SAMPLE_HEADERS],
  })
  XLSX.utils.book_append_sheet(workbook, sheet, 'Data')
  XLSX.writeFile(workbook, GENOMIC_MATRIX_FIXTURE_PATH)
  return GENOMIC_MATRIX_FIXTURE_PATH
}

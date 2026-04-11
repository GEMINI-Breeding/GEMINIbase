/**
 * Generate a multi-sheet XLSX fixture for the trait import wizard e2e test.
 *
 * Each sheet has the same column layout (Accession, Plot, Row, Column,
 * Yield_kg, Moisture) but different values, so the column-mapping step can
 * verify header-match carry-forward across sheets.
 */
import * as XLSX from 'xlsx'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

interface Row {
  Accession: string
  Plot: number
  Row: number
  Column: number
  Yield_kg: number
  Moisture: number
  Notes: string
}

const year1Rows: Row[] = [
  { Accession: 'G001', Plot: 1, Row: 1, Column: 1, Yield_kg: 4.2, Moisture: 12.3, Notes: 'clean' },
  { Accession: 'G002', Plot: 2, Row: 1, Column: 2, Yield_kg: 3.8, Moisture: 13.1, Notes: 'edge effect' },
  { Accession: 'G003', Plot: 3, Row: 2, Column: 1, Yield_kg: 4.5, Moisture: 12.8, Notes: 'clean' },
]

const year2Rows: Row[] = [
  { Accession: 'G001', Plot: 1, Row: 1, Column: 1, Yield_kg: 4.6, Moisture: 11.9, Notes: 'dry spell' },
  { Accession: 'G002', Plot: 2, Row: 1, Column: 2, Yield_kg: 4.0, Moisture: 12.5, Notes: 'clean' },
  { Accession: 'G003', Plot: 3, Row: 2, Column: 1, Yield_kg: 4.8, Moisture: 12.1, Notes: 'clean' },
]

export const MULTI_TRAIT_FIXTURE_PATH = path.join(
  __dirname,
  'multi_trait_measurements.xlsx',
)

export const MULTI_TRAIT_FIXTURE = {
  path: MULTI_TRAIT_FIXTURE_PATH,
  sheets: {
    Year1: year1Rows,
    Year2: year2Rows,
  },
  /** Total records per trait (3 rows × 2 sheets). */
  recordsPerTrait: 6,
} as const

export function generateMultiTraitFixture(): string {
  const workbook = XLSX.utils.book_new()
  const sheet1 = XLSX.utils.json_to_sheet(year1Rows)
  XLSX.utils.book_append_sheet(workbook, sheet1, 'Year1')
  const sheet2 = XLSX.utils.json_to_sheet(year2Rows)
  XLSX.utils.book_append_sheet(workbook, sheet2, 'Year2')
  XLSX.writeFile(workbook, MULTI_TRAIT_FIXTURE_PATH)
  return MULTI_TRAIT_FIXTURE_PATH
}

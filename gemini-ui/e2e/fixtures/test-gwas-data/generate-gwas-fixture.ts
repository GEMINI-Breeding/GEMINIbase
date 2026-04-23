/**
 * Generate synthetic genomic + trait XLSX fixtures for the GWAS e2e test.
 *
 * The output mimics the structure of real inputs the user has on disk:
 *
 *   - genomic: row 1 = title, row 2 = header [SNP Name, Design sequence,
 *     SNP allele, Chr, cM, <accessions…>], rows 3+ = variants with diploid
 *     string calls ("TT"/"TC"/"CC"/"NN"). 50 SNPs across 2 chromosomes
 *     spaced 1 cM apart so the PLINK bim writer doesn't have to disambiguate.
 *   - trait: single sheet, columns = [Line ID, Plot, Stand_count,
 *     Plant_height], one row per accession.
 *
 * Everything is seeded for determinism. Numbers are small (20 samples × 50
 * SNPs) so the GWAS run finishes in < 1 minute.
 */
import * as XLSX from 'xlsx'
import fs from 'node:fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export const SAMPLE_COUNT = 20
export const VARIANT_COUNT = 50
export const CHROMOSOMES = 2
const SEED = 42

export const SAMPLE_NAMES: string[] = Array.from(
  { length: SAMPLE_COUNT },
  (_, i) => `E2E_MAGIC${String(i + 1).padStart(3, '0')}`,
)

export const GENOMIC_FIXTURE_PATH = path.join(__dirname, 'gwas-genomic.xlsx')
export const TRAIT_FIXTURE_PATH = path.join(__dirname, 'gwas-trait.xlsx')

// Allele pairs used when building variants. Deliberately biallelic SNPs.
const ALLELE_POOL: Array<[string, string]> = [
  ['T', 'C'],
  ['A', 'G'],
  ['C', 'T'],
  ['G', 'A'],
]

// Minimal seeded PRNG — reproducible output across runs/machines.
function mulberry32(seed: number): () => number {
  let t = seed >>> 0
  return () => {
    t = (t + 0x6d2b79f5) >>> 0
    let x = t
    x = Math.imul(x ^ (x >>> 15), x | 1)
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61)
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

function genotypeCall(rand: () => number, ref: string, alt: string): string {
  // ~3% missing, otherwise random among hom-ref / het / hom-alt.
  const r = rand()
  if (r < 0.03) return 'NN'
  if (r < 0.35) return `${ref}${ref}`
  if (r < 0.70) return `${ref}${alt}`
  return `${alt}${alt}`
}

export const GENOMIC_FIXTURE = {
  path: GENOMIC_FIXTURE_PATH,
  sampleNames: SAMPLE_NAMES,
  variantCount: VARIANT_COUNT,
  chromosomes: CHROMOSOMES,
} as const

export const TRAIT_FIXTURE = {
  path: TRAIT_FIXTURE_PATH,
  /** Single trait label in the generated spreadsheet header. */
  traitColumns: ['Stand_count', 'Plant_height'] as const,
} as const

export function generateGwasFixture(): { genomicPath: string; traitPath: string } {
  const rand = mulberry32(SEED)

  // ── Genomic workbook ─────────────────────────────────────────────────
  // aoa_to_sheet preserves the two-row header (title + real header).
  const titleRow = [
    'SUPPORTING DATA (synthetic e2e fixture): polymorphic SNPs + genotypes for MAGIC test accessions',
  ]
  const headerRow = ['SNP Name', 'Design sequence', 'SNP allele', 'Chr', 'cM', ...SAMPLE_NAMES]

  const variantRows: (string | number)[][] = []
  const perChrom = Math.ceil(VARIANT_COUNT / CHROMOSOMES)
  for (let v = 0; v < VARIANT_COUNT; v++) {
    const chrom = Math.floor(v / perChrom) + 1
    const cm = (v % perChrom) * 1 // 1-cM spacing within each chromosome
    const [ref, alt] = ALLELE_POOL[v % ALLELE_POOL.length]
    const design = `NNN[${ref}/${alt}]NNN`
    const alleles = `${ref}/${alt}`
    const row: (string | number)[] = [`snp_${v + 1}`, design, alleles, chrom, cm]
    for (let s = 0; s < SAMPLE_COUNT; s++) {
      row.push(genotypeCall(rand, ref, alt))
    }
    variantRows.push(row)
  }

  const genomicWb = XLSX.utils.book_new()
  const genomicSheet = XLSX.utils.aoa_to_sheet([titleRow, headerRow, ...variantRows])
  XLSX.utils.book_append_sheet(genomicWb, genomicSheet, 'Data')
  XLSX.writeFile(genomicWb, GENOMIC_FIXTURE_PATH)

  // ── Trait workbook ───────────────────────────────────────────────────
  interface TraitRow {
    'Line ID': string
    Plot: number
    Stand_count: number
    Plant_height: number
  }
  const traitRows: TraitRow[] = SAMPLE_NAMES.map((name, i) => ({
    'Line ID': name,
    Plot: i + 1,
    Stand_count: 10 + Math.floor(rand() * 41), // 10–50
    Plant_height: Number((30 + rand() * 90).toFixed(1)), // 30–120
  }))
  const traitWb = XLSX.utils.book_new()
  const traitSheet = XLSX.utils.json_to_sheet(traitRows)
  XLSX.utils.book_append_sheet(traitWb, traitSheet, 'Data')
  XLSX.writeFile(traitWb, TRAIT_FIXTURE_PATH)

  return { genomicPath: GENOMIC_FIXTURE_PATH, traitPath: TRAIT_FIXTURE_PATH }
}

/** Remove the generated workbooks. Safe to call without a prior generate. */
export function cleanupGwasFixture(): void {
  for (const p of [GENOMIC_FIXTURE_PATH, TRAIT_FIXTURE_PATH]) {
    try {
      fs.unlinkSync(p)
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== 'ENOENT') throw err
    }
  }
}

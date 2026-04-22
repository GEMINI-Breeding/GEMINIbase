import { test, expect, type APIRequestContext } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'
import {
  generateGenomicMatrixFixture,
  GENOMIC_MATRIX_FIXTURE,
  GENOMIC_FIXTURE_RUN_TOKEN,
} from './fixtures/test-genomic-data/generate-genomic-matrix'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * End-to-end test for the genomic import wizard. Covers the full happy path
 * for a matrix-xlsx file that the detection engine must identify as a
 * genomic matrix (not a trait table), route to the genomic wizard, resolve
 * sample headers (with auto-create for unresolved), create variants,
 * ingest genotype records, and land the user on the study detail page.
 */

const TEST_RUN_ID = `e2e-genomic-${Date.now()}`
const STUDY_NAME = `E2E Genomic Study ${TEST_RUN_ID}`

async function cleanupGenomicTestEntities(
  request: APIRequestContext,
  nameContains: string,
) {
  // Delete studies first — this also cleans up their genotype records via
  // cascade. Accession + variant cleanup is best-effort; the backend
  // enforces unique names so re-running the test is safe either way.
  for (const endpoint of ['genotyping_studies', 'accessions']) {
    try {
      const res = await request.get(`/api/${endpoint}/all`, {
        params: { limit: '500' },
      })
      if (!res.ok()) continue
      const items = await res.json()
      if (!Array.isArray(items)) continue
      const nameField =
        endpoint === 'genotyping_studies' ? 'study_name' : 'accession_name'
      for (const item of items) {
        const name: string = item[nameField] ?? ''
        if (name.includes(nameContains)) {
          try {
            await request.delete(`/api/${endpoint}/id/${item.id}`)
          } catch {
            // ignore individual delete failures
          }
        }
      }
    } catch {
      // ignore fetch failures (empty list returns 404)
    }
  }
}

test.describe.serial('Genomic Import Workflow — matrix xlsx', () => {
  test.setTimeout(120_000)

  let studyId: string

  test.beforeAll(async ({ request }) => {
    // Best-effort clean up of stale per-run entities. Sample accessions
    // are embedded with GENOMIC_FIXTURE_RUN_TOKEN so repeated runs don't
    // collide and the "unresolved" branch is exercised each time.
    await cleanupGenomicTestEntities(request, TEST_RUN_ID)
    await cleanupGenomicTestEntities(request, GENOMIC_FIXTURE_RUN_TOKEN)
    generateGenomicMatrixFixture()
  })

  test('import matrix xlsx via genomic wizard', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: 'Import Data' })).toBeVisible()

    // Step 1: Detect — drop the genomic matrix xlsx. Detection should tag
    // it `genomic` and surface the matrix shape, which routes us to the
    // GenomicWizard instead of the trait flow.
    const fileInput = page.locator('[data-testid="dropzone"] input[type="file"]')
    await fileInput.setInputFiles([GENOMIC_MATRIX_FIXTURE.path])

    await expect(page.getByTestId('detection-summary')).toBeVisible({ timeout: 10_000 })
    // Genomic badge signals the wizard has categorized the file correctly.
    await expect(page.getByText(/Genomic/i).first()).toBeVisible()

    await page.getByTestId('detect-continue').click()

    // From here on we should be inside the GenomicWizard, not the trait wizard.
    await expect(page.getByTestId('genomic-wizard')).toBeVisible({ timeout: 10_000 })

    // Step 2: Metadata — create a new study with a unique name.
    await expect(page.getByTestId('genomic-file-summary')).toBeVisible()
    await page.getByTestId('select-study').selectOption('__create_new__')
    await page.getByTestId('new-study-name').fill(STUDY_NAME)

    await page.getByTestId('genomic-metadata-continue').click()

    // Step 3: Sample resolve — all 4 sample headers are brand-new on a
    // clean DB, so the resolver will surface them as unresolved. Wait for
    // the unresolved-action panel to actually render before clicking
    // "Auto-create accessions for all".
    await expect(page.getByTestId('sample-resolve-summary')).toBeVisible({
      timeout: 15_000,
    })
    await expect(page.getByTestId('unresolved-action')).toBeVisible({
      timeout: 15_000,
    })
    await page.getByTestId('unresolved-create-all').click()
    await expect(page.getByTestId('sample-resolve-continue')).toBeEnabled({
      timeout: 5_000,
    })
    await page.getByTestId('sample-resolve-continue').click()

    // Step 4: Ingest — run through entity creation, file upload, and
    // matrix ingest. Wait until the Continue button enables.
    await expect(page.getByTestId('genomic-ingest-status')).toBeVisible()
    await expect(page.getByTestId('genomic-ingest-continue')).toBeEnabled({
      timeout: 60_000,
    })

    // Progress card should reflect the 10 variants × 4 samples = 40 records.
    await expect(page.getByTestId('genomic-ingest-progress')).toContainText(
      'Genotype records inserted',
    )

    await page.getByTestId('genomic-ingest-continue').click()

    // Step 5: Confirm
    await expect(page.getByTestId('genomic-confirm-heading')).toHaveText(
      'Genomic Import Complete',
    )

    // Cross-check via API — study should exist with matching name.
    const res = await page.request.get('/api/genotyping_studies', {
      params: { study_name: STUDY_NAME },
    })
    expect(res.ok()).toBeTruthy()
    const studies = await res.json()
    const study = (Array.isArray(studies) ? studies : []).find(
      (s: { study_name: string }) => s.study_name === STUDY_NAME,
    )
    expect(study).toBeTruthy()
    studyId = study.id
  })

  test('genotype records landed and study detail page shows them', async ({ page }) => {
    const recordsRes = await page.request.get(
      `/api/genotyping_studies/id/${studyId}/records`,
      { params: { limit: '100' } },
    )
    expect(recordsRes.ok()).toBeTruthy()
    const records = await recordsRes.json()
    // 10 variants × 4 samples = 40 records expected (all calls non-null).
    expect(Array.isArray(records) && records.length).toBeGreaterThanOrEqual(30)

    await page.goto(`/genotyping-studies/${studyId}`)
    await expect(page.getByRole('heading', { name: STUDY_NAME })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByTestId('tab-records').click()
    // One of the SNP names from the fixture.
    await expect(
      page.getByText(`${GENOMIC_FIXTURE_RUN_TOKEN}_snp_001`).first(),
    ).toBeVisible({ timeout: 10_000 })

    await cleanupGenomicTestEntities(page.request, TEST_RUN_ID)
    await cleanupGenomicTestEntities(page.request, GENOMIC_FIXTURE_RUN_TOKEN)
  })
})

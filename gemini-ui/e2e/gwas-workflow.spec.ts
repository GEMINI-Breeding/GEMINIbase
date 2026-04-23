import { test, expect } from '@playwright/test'
import { cleanupTestEntities } from './helpers/cleanup'
import {
  cleanupGwasFixture,
  generateGwasFixture,
  GENOMIC_FIXTURE,
  TRAIT_FIXTURE,
  SAMPLE_NAMES,
} from './fixtures/test-gwas-data/generate-gwas-fixture'

/**
 * End-to-end smoke test for the full GWAS workflow.
 *
 *   1. Generate small synthetic genomic + trait XLSX fixtures.
 *   2. Import genomic data through the UI wizard (/import → genomic path).
 *   3. Import trait data through the UI wizard (/import → trait path),
 *      with Line ID as the germplasm column so accessions get re-used.
 *   4. Verify the data landed in the backend and renders in the UI.
 *   5. Submit a GWAS via /gwas and assert the job completes with the
 *      expected artifacts + statistics (p-values in [0, 1], Manhattan + QQ
 *      plots rendered, all 20 samples had matching phenotypes).
 *
 * The numbers are intentionally fake; we only check structural correctness,
 * not statistical signal.
 */

const TEST_RUN_ID = `e2e-gwas-${Date.now()}`
const PREFIX = `E2E_GWAS_${TEST_RUN_ID}`
const STUDY_NAME = `${PREFIX}_Study`
const EXPERIMENT = `${PREFIX}_Experiment`
const SEASON = `${PREFIX}_Season`
const SITE = `${PREFIX}_Site`
const DATASET = `${PREFIX}_Dataset`
const TRAIT_LABEL = `${PREFIX}_Stand_Count`

// Captured during the run and asserted in later tests.
let studyId: string
let experimentId: string
let datasetId: string
let traitId: string
let jobId: string

test.describe.serial('GWAS end-to-end workflow', () => {
  test.setTimeout(300_000)

  test.beforeAll(async ({ request }) => {
    // Two sweeps because the spec creates entities under two distinct name
    // prefixes: "E2E_GWAS_…" for the study/experiment/dataset/trait/site/season
    // and "E2E_MAGIC###" for every accession + line. Procedurally generated
    // variants ("snp_1"…"snp_50") are cleaned up transitively when the study
    // is deleted — GenotypingStudy.delete() cascades to genotype_records and
    // to orphan variants. A fresh afterAll so a killed mid-run doesn't leave
    // dangling state for the next invocation.
    await cleanupTestEntities(request, 'E2E_GWAS')
    await cleanupTestEntities(request, 'E2E_MAGIC')
    await cleanupTestEntities(request, 'snp_')
    generateGwasFixture()
  })

  test.afterAll(async ({ request }) => {
    await cleanupTestEntities(request, 'E2E_GWAS')
    await cleanupTestEntities(request, 'E2E_MAGIC')
    await cleanupTestEntities(request, 'snp_')
    cleanupGwasFixture()
  })

  // -------------------------------------------------------------------------
  // 1. Import genomic data via the UI
  // -------------------------------------------------------------------------
  test('imports genomic data via the UI wizard', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: 'Import Data' })).toBeVisible()

    // Detect step — the wizard shell only routes to the GenomicWizard after
    // the user clicks through the detect step; detection categorization is
    // populated into state by handleDetectNext.
    const fileInput = page.locator('[data-testid="dropzone"] input[type="file"]')
    await fileInput.setInputFiles([GENOMIC_FIXTURE.path])
    await expect(page.getByTestId('detection-summary')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('detect-continue').click()

    // Metadata step (genomic wizard)
    await expect(page.getByTestId('select-study')).toBeVisible({ timeout: 30_000 })
    await page.getByTestId('select-study').selectOption('__create_new__')
    await page.getByTestId('new-study-name').fill(STUDY_NAME)
    await page.getByTestId('select-experiment').selectOption('__create_new_experiment__')
    await page.getByTestId('new-experiment-name').fill(EXPERIMENT)
    await page.getByTestId('genomic-metadata-continue').click()

    // Sample resolve: the step fires an async /api/germplasm_resolver/resolve
    // call. When any samples are new (clean DB) the unresolved-action panel
    // appears; when every header matches an existing accession, the panel
    // is skipped and continue is enabled directly. Wait up to 30 s for the
    // panel — absence means the all-resolved path.
    await expect(page.getByTestId('sample-resolve-summary')).toBeVisible({ timeout: 30_000 })
    const unresolvedAction = page.getByTestId('unresolved-action')
    await unresolvedAction.waitFor({ state: 'visible', timeout: 30_000 }).catch(() => {})
    if (await unresolvedAction.isVisible()) {
      await page.getByTestId('unresolved-create-all').click()
    }
    const resolveContinue = page.getByTestId('sample-resolve-continue')
    await expect(resolveContinue).toBeEnabled({ timeout: 60_000 })
    await resolveContinue.click()

    // Ingest step — 20 samples × 50 variants = 1000 rows; comfortably under 2 min.
    await expect(page.getByTestId('genomic-ingest-status')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByTestId('genomic-ingest-continue')).toBeEnabled({ timeout: 180_000 })
    await page.getByTestId('genomic-ingest-continue').click()

    // Confirm step
    await expect(page.getByTestId('genomic-confirm-heading')).toHaveText(
      /Genomic Import Complete/i,
    )
  })

  // -------------------------------------------------------------------------
  // 2. Import trait data via the UI (line-only germplasm, reuses accessions)
  // -------------------------------------------------------------------------
  test('imports trait data via the UI wizard', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: 'Import Data' })).toBeVisible()

    const fileInput = page.locator('[data-testid="dropzone"] input[type="file"]')
    await fileInput.setInputFiles([TRAIT_FIXTURE.path])

    await expect(page.getByTestId('detection-summary')).toBeVisible({ timeout: 15_000 })
    await page.getByTestId('detect-continue').click()

    // Metadata step — only Experiment + Dataset Name live here now; season
    // and site are configured in the column-mapping step below. When the
    // dropdown has existing options (the genomic import created ours),
    // pick "+ Create new..." explicitly and type the same name — the
    // backend's get_or_create dedupes.
    await expect(page.getByText('Configure Import Metadata')).toBeVisible()
    await page.getByTestId('select-experiment').selectOption('__create_new__')
    await page.getByTestId('new-experiment').fill(EXPERIMENT)
    await page.getByTestId('dataset-name-0').fill(DATASET)
    await page.getByTestId('metadata-continue').click()

    // Column mapping: map plot number, trait column, and the Line ID column
    // as the germplasm anchor — keeps the wizard in line-only mode so it
    // skips the ambiguous-resolve step and so the trait import's idempotent
    // get_or_create finds the accessions the genomic wizard just created.
    await expect(page.getByRole('heading', { name: 'Data Preview' })).toBeVisible({
      timeout: 15_000,
    })
    await page.getByTestId('plot-number-select').selectOption('Plot')
    await page.getByTestId('trait-checkbox-Stand_count').check()
    const traitLabel = page.getByTestId('trait-label-Stand_count')
    await traitLabel.clear()
    await traitLabel.fill(TRAIT_LABEL)
    await page.getByTestId('trait-units-Stand_count').fill('count')
    await page.getByTestId('line-name-column-select').selectOption('Line ID')

    // Season / site / date: fixed values (no per-row column in our fixture).
    await page.getByTestId('season-mode').selectOption('fixed')
    await page.getByTestId('season-fixed').fill(SEASON)
    await page.getByTestId('site-mode').selectOption('fixed')
    await page.getByTestId('site-fixed').fill(SITE)
    await page.getByTestId('collection-date-mode').selectOption('unknown')

    await page.getByTestId('mapping-continue').click()

    // Germplasm review — line-only mode usually skips this entirely. If it
    // does appear, the Continue button will be enabled immediately because
    // every Line ID already maps to an existing Accession.
    const germplasmReviewContinue = page.getByTestId('germplasm-review-continue')
    if (await germplasmReviewContinue.isVisible().catch(() => false)) {
      await expect(germplasmReviewContinue).toBeEnabled({ timeout: 30_000 })
      await germplasmReviewContinue.click()
    }

    // Upload + ingestion
    await expect(page.getByText('Creating Entities')).toBeVisible({ timeout: 30_000 })
    await expect(page.getByTestId('upload-continue')).toBeEnabled({ timeout: 120_000 })
    await page.getByTestId('upload-continue').click()

    // Confirm
    await expect(page.getByTestId('confirm-heading')).toHaveText(/Import Complete/i)
  })

  // -------------------------------------------------------------------------
  // 3. Verify data landed in the backend + is visible in the UI
  // -------------------------------------------------------------------------
  test('verifies data landed in the backend and renders in the UI', async ({
    page,
    request,
  }) => {
    // Genotyping study
    const studiesRes = await request.get('/api/genotyping_studies/all', {
      params: { limit: '500' },
    })
    const studies = await studiesRes.json()
    const study = (Array.isArray(studies) ? studies : []).find(
      (s: { study_name: string }) => s.study_name === STUDY_NAME,
    )
    expect(study, `Expected genotyping study "${STUDY_NAME}" to exist`).toBeTruthy()
    studyId = study.id

    // Experiment
    const expRes = await request.get('/api/experiments/all', { params: { limit: '500' } })
    const experiments = await expRes.json()
    const exp = (Array.isArray(experiments) ? experiments : []).find(
      (e: { experiment_name: string }) => e.experiment_name === EXPERIMENT,
    )
    expect(exp, `Expected experiment "${EXPERIMENT}" to exist`).toBeTruthy()
    experimentId = exp.id

    // Dataset (via experiment scope)
    const dsRes = await request.get('/api/datasets/all', { params: { limit: '500' } })
    const datasets = await dsRes.json()
    const ds = (Array.isArray(datasets) ? datasets : []).find(
      (d: { dataset_name: string }) => d.dataset_name === DATASET,
    )
    expect(ds, `Expected dataset "${DATASET}" to exist`).toBeTruthy()
    datasetId = ds.id

    // Trait — use the new dataset→traits endpoint.
    const traitsRes = await request.get(`/api/datasets/id/${datasetId}/traits`)
    const traits = await traitsRes.json()
    const trait = (Array.isArray(traits) ? traits : []).find(
      (t: { trait_name: string }) => t.trait_name === TRAIT_LABEL,
    )
    expect(trait, `Expected trait "${TRAIT_LABEL}" to exist under dataset`).toBeTruthy()
    traitId = trait.id

    // Accession count: every genomic column header should have become an
    // Accession. (Trait-side get_or_create reuses those rows, not creating
    // duplicates.) 500 is enough headroom even against a lived-in dev DB.
    const accRes = await request.get('/api/accessions/all', { params: { limit: '1000' } })
    const accessions = await accRes.json()
    const e2eNames = (Array.isArray(accessions) ? accessions : [])
      .map((a: { accession_name: string }) => a.accession_name)
      .filter((name: string) => SAMPLE_NAMES.includes(name))
    expect(e2eNames).toHaveLength(SAMPLE_NAMES.length)

    // UI sanity: the list pages render the new entities without errors.
    await page.goto('/genotyping-studies')
    await expect(page.getByText(STUDY_NAME)).toBeVisible({ timeout: 15_000 })
    await page.goto('/traits')
    await expect(page.getByText(TRAIT_LABEL)).toBeVisible({ timeout: 15_000 })
  })

  // -------------------------------------------------------------------------
  // 4. Run a GWAS via /gwas and verify the result
  // -------------------------------------------------------------------------
  test('runs a GWAS via /gwas and verifies completion', async ({ page, request }) => {
    await page.goto('/gwas')

    // Pick source entities. All four are plain <select>s.
    await page.getByTestId('gwas-experiment-select').selectOption({ label: EXPERIMENT })
    await page.getByTestId('gwas-study-select').selectOption({ label: STUDY_NAME })
    await page.getByTestId('gwas-dataset-select').selectOption({ label: DATASET })
    await page.getByTestId(`gwas-trait-checkbox-${TRAIT_LABEL}`).check()

    // Loosen QC and skip PCs — with 20 samples and random genotypes we
    // want the pipeline to reach GEMMA reliably, not fight our noise.
    await page.getByTestId('gwas-advanced-toggle').click()
    await page.getByTestId('gwas-qc-maf').fill('0.01')
    // n_pcs is a range input — 0 = intercept-only covariate path.
    const slider = page.getByTestId('gwas-npcs-slider')
    await slider.focus()
    await slider.fill('0')

    await page.getByTestId('gwas-submit').click()

    // Navigation to /gwas/$jobId gives us the job id to poll.
    await page.waitForURL(/\/gwas\/[0-9a-f-]{36}$/, { timeout: 30_000 })
    jobId = page.url().split('/').pop()!
    expect(jobId).toMatch(/^[0-9a-f-]{36}$/)

    // Poll REST directly — faster and less flaky than watching the progress bar.
    // The backend returns uppercase statuses (COMPLETED / FAILED); normalise
    // to lowercase and wait for any terminal state, then assert it's the
    // success state so we get the real error_message on failure.
    const TERMINAL = new Set(['completed', 'failed', 'cancelled'])
    await expect
      .poll(
        async () => {
          const res = await request.get(`/api/jobs/${jobId}`)
          if (!res.ok()) return false
          const j = await res.json()
          return TERMINAL.has(String(j.status ?? '').toLowerCase())
        },
        {
          intervals: [2_000, 3_000, 5_000, 5_000, 5_000],
          timeout: 240_000,
          message: `GWAS job ${jobId} did not reach a terminal state within 240s`,
        },
      )
      .toBe(true)

    const jobRes0 = await request.get(`/api/jobs/${jobId}`)
    const job0 = await jobRes0.json()
    const finalStatus = String(job0.status ?? '').toLowerCase()
    expect(finalStatus, `job error_message: ${job0.error_message}`).toBe('completed')

    // Inspect the result payload.
    const jobRes = await request.get(`/api/jobs/${jobId}`)
    const job = await jobRes.json()
    const result = job.result as Record<string, unknown>
    expect(result, 'job.result should be populated').toBeTruthy()

    const artifacts = result.artifacts as Record<string, string>
    expect(artifacts.manhattan).toMatch(/s3:\/\/.+\/manhattan\.png$/)
    expect(artifacts.qq).toMatch(/s3:\/\/.+\/qq\.png$/)
    expect(artifacts.assoc).toMatch(/s3:\/\/.+\/run\.assoc\.txt$/)

    expect(result.n_variants_passed_qc as number).toBeGreaterThanOrEqual(1)
    expect(result.n_samples_with_phenotype).toBe(SAMPLE_NAMES.length)

    const lambda = result.genomic_inflation_lambda as number
    expect(typeof lambda).toBe('number')
    expect(Number.isFinite(lambda)).toBe(true)

    const topHits = result.top_hits as Array<{ p: number; rs: string }>
    expect(Array.isArray(topHits)).toBe(true)
    expect(topHits.length).toBeGreaterThanOrEqual(1)
    for (const hit of topHits) {
      expect(hit.p).toBeGreaterThan(0)
      expect(hit.p).toBeLessThanOrEqual(1)
    }

    // UI-side assertions: reload so the polling query refetches and paints
    // the completed state, then check the artifacts actually render.
    await page.reload()
    await expect(page.getByTestId('gwas-result-summary')).toBeVisible({ timeout: 30_000 })

    const manhattanImg = page.getByTestId('gwas-manhattan-img')
    const qqImg = page.getByTestId('gwas-qq-img')
    await expect(manhattanImg).toBeVisible()
    await expect(qqImg).toBeVisible()

    await expect(async () => {
      const loaded = await manhattanImg.evaluate(
        (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
      )
      expect(loaded).toBe(true)
    }).toPass({ timeout: 15_000 })
    await expect(async () => {
      const loaded = await qqImg.evaluate(
        (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
      )
      expect(loaded).toBe(true)
    }).toPass({ timeout: 15_000 })

    const topHitsRows = page.locator('[data-testid="gwas-top-hits-table"] tbody tr')
    expect(await topHitsRows.count()).toBeGreaterThanOrEqual(1)
  })
})

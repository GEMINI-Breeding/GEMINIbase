import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'
import { cleanupTestEntities } from './helpers/cleanup'
import { generateMultiTraitFixture, MULTI_TRAIT_FIXTURE } from './fixtures/test-trait-data/generate-multi-trait'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * End-to-end tests for the redesigned trait import wizard.
 *
 * Two scenarios:
 *   1. Single-sheet CSV → single trait column (smoke test for simple case).
 *   2. Multi-sheet XLSX → multiple trait columns, per-sheet configuration,
 *      header-match carry-forward, two distinct traits ingested.
 */

const CSV_FIXTURE = path.join(__dirname, 'fixtures', 'test-trait-data', 'stand_count_measurements.csv')
const TEST_RUN_ID = `e2e-trait-${Date.now()}`

// -----------------------------------------------------------------------------
// Scenario 1: single-sheet CSV, one trait column
// -----------------------------------------------------------------------------

const EXPERIMENT_NAME = `E2E Trait Experiment ${TEST_RUN_ID}`
const SEASON_NAME = `E2E Trait Season ${TEST_RUN_ID}`
const SITE_NAME = `E2E Trait Site ${TEST_RUN_ID}`
const DATASET_NAME = `E2E Trait Dataset ${TEST_RUN_ID}`
const TRAIT_NAME = `Stand Count ${TEST_RUN_ID}`

let experimentId: string

test.describe.serial('Trait Import Workflow — single-sheet CSV', () => {
  test.setTimeout(120_000)

  test.beforeAll(async ({ request }) => {
    await cleanupTestEntities(request, 'E2E Trait')
    await cleanupTestEntities(request, 'Stand Count')
  })

  test('import CSV with a single trait column', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: 'Import Data' })).toBeVisible()

    // ── Step 1: Detect ──
    const fileInput = page.locator('[data-testid="dropzone"] input[type="file"]')
    await fileInput.setInputFiles([CSV_FIXTURE])

    await expect(page.getByTestId('detection-summary')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('1 file')).toBeVisible()

    await page.getByTestId('detect-continue').click()

    // ── Step 2: Metadata ──
    await expect(page.getByText('Configure Import Metadata')).toBeVisible()

    await expect(page.getByTestId('new-sensor')).not.toBeVisible()
    await expect(page.getByTestId('new-sensor-platform')).not.toBeVisible()

    const expInput = page.getByTestId('new-experiment')
    await expInput.clear()
    await expInput.fill(EXPERIMENT_NAME)

    const seasonInput = page.getByTestId('new-season')
    await seasonInput.clear()
    await seasonInput.fill(SEASON_NAME)

    const siteInput = page.getByTestId('new-site')
    await siteInput.clear()
    await siteInput.fill(SITE_NAME)

    const datasetInput = page.getByTestId('dataset-name-0')
    await datasetInput.clear()
    await datasetInput.fill(DATASET_NAME)

    await page.getByTestId('metadata-continue').click()

    // ── Step 3: Column Mapping (single sheet) ──
    await expect(page.getByRole('heading', { name: 'Data Preview' })).toBeVisible({ timeout: 10_000 })
    // For a 1-sheet file, the Next-sheet button should be disabled.
    await expect(page.getByTestId('sheet-next')).toBeDisabled()
    await expect(page.getByTestId('sheet-prev')).toBeDisabled()

    // Plot number is the required row identifier. Row and Column are optional.
    await page.getByTestId('plot-number-select').selectOption('Plot')
    await page.getByTestId('plot-row-select').selectOption('Row')
    await page.getByTestId('plot-col-select').selectOption('Column')

    // Check "Stand Count" as the trait column and rename its label.
    await page.getByTestId('trait-checkbox-Stand Count').check()
    const traitLabelInput = page.getByTestId('trait-label-Stand Count')
    await traitLabelInput.clear()
    await traitLabelInput.fill(TRAIT_NAME)

    // Add the Date column as free-form metadata (demonstrates the new
    // metadata picker).
    await page.getByTestId('metadata-add-select').selectOption('Date')
    await page.getByTestId('metadata-add-button').click()
    await expect(page.getByTestId('metadata-label-Date')).toHaveValue('Date')

    // Mapped preview renders once plot # + at least one trait is picked.
    await expect(page.getByRole('heading', { name: 'Mapped Preview' })).toBeVisible()

    await page.getByTestId('mapping-continue').click()

    // ── Step 4: Upload + Ingestion ──
    await expect(page.getByText('Creating Entities')).toBeVisible()
    await expect(page.getByTestId('upload-continue')).toBeEnabled({ timeout: 60_000 })

    // Record ingestion panel should show 5 records for our single trait.
    await expect(page.getByTestId('ingestion-progress')).toBeVisible()
    await expect(page.getByTestId('ingestion-progress')).toContainText('5 / 5 records')

    await page.getByTestId('upload-continue').click()

    // ── Step 5: Confirm ──
    await expect(page.getByTestId('confirm-heading')).toHaveText('Import Complete')

    const expRes = await page.request.get('/api/experiments', {
      params: { experiment_name: EXPERIMENT_NAME },
    })
    const experiments = await expRes.json()
    const exp = experiments.find((e: { experiment_name: string }) => e.experiment_name === EXPERIMENT_NAME)
    expect(exp).toBeTruthy()
    experimentId = exp.id
  })

  test('verify trait records were ingested into the database', async ({ page }) => {
    const traitRes = await page.request.get('/api/traits/all', { params: { limit: '100' } })
    const allTraits = await traitRes.json()
    const trait = (Array.isArray(allTraits) ? allTraits : []).find(
      (t: { trait_name: string }) => t.trait_name === TRAIT_NAME,
    )
    expect(trait).toBeTruthy()

    const datasetsRes = await page.request.get('/api/datasets/all', { params: { limit: '500' } })
    const allDatasets = await datasetsRes.json()
    const dataset = (Array.isArray(allDatasets) ? allDatasets : []).find(
      (d: { dataset_name: string }) => d.dataset_name === DATASET_NAME,
    )
    expect(dataset).toBeTruthy()

    await page.goto(`/experiments/${experimentId}`)
    await expect(page.getByRole('heading', { name: EXPERIMENT_NAME })).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('count-traits')).not.toHaveText('0', { timeout: 10_000 })
    await expect(page.getByTestId('count-datasets')).not.toHaveText('0', { timeout: 10_000 })

    await cleanupTestEntities(page.request, TEST_RUN_ID)
  })
})

// -----------------------------------------------------------------------------
// Scenario 2: multi-sheet XLSX, multiple trait columns, header-match carryover
// -----------------------------------------------------------------------------

const MULTI_RUN_ID = `e2e-multi-${Date.now()}`
const MULTI_EXPERIMENT = `E2E Multi Experiment ${MULTI_RUN_ID}`
const MULTI_SEASON = `E2E Multi Season ${MULTI_RUN_ID}`
const MULTI_SITE = `E2E Multi Site ${MULTI_RUN_ID}`
const MULTI_DATASET = `E2E Multi Dataset ${MULTI_RUN_ID}`
const YIELD_TRAIT = `Grain Yield ${MULTI_RUN_ID}`
const MOISTURE_TRAIT = `Moisture ${MULTI_RUN_ID}`

test.describe.serial('Trait Import Workflow — multi-sheet XLSX', () => {
  test.setTimeout(180_000)

  test.beforeAll(async ({ request }) => {
    await cleanupTestEntities(request, 'E2E Multi')
    await cleanupTestEntities(request, MULTI_RUN_ID)
    // Generate the xlsx fixture on disk (not checked in).
    generateMultiTraitFixture()
  })

  test('walks through both sheets with carry-forward and ingests two traits', async ({ page }) => {
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: 'Import Data' })).toBeVisible()

    // Upload the multi-sheet xlsx
    const fileInput = page.locator('[data-testid="dropzone"] input[type="file"]')
    await fileInput.setInputFiles([MULTI_TRAIT_FIXTURE.path])
    await expect(page.getByTestId('detection-summary')).toBeVisible({ timeout: 10_000 })
    await page.getByTestId('detect-continue').click()

    // Fill metadata
    await expect(page.getByText('Configure Import Metadata')).toBeVisible()
    await page.getByTestId('new-experiment').fill(MULTI_EXPERIMENT)
    await page.getByTestId('new-season').fill(MULTI_SEASON)
    await page.getByTestId('new-site').fill(MULTI_SITE)
    await page.getByTestId('dataset-name-0').fill(MULTI_DATASET)
    await page.getByTestId('metadata-continue').click()

    // ── Column mapping, Sheet 1 "Year1" ──
    await expect(page.getByRole('heading', { name: 'Data Preview' })).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText('Sheet 1 of 2:')).toBeVisible()
    await expect(page.getByText('Year1')).toBeVisible()

    // Map plot columns — plot number is required, row/col optional.
    await page.getByTestId('plot-number-select').selectOption('Plot')
    await page.getByTestId('plot-row-select').selectOption('Row')
    await page.getByTestId('plot-col-select').selectOption('Column')

    // Germplasm: map the Accession column as the accession-name role. This
    // opts the run into the germplasm review step, which we then handle
    // further down (the e2e test asserts every "Accession" value
    // already exists, so the review step should show 0 unresolved and let
    // us continue without making decisions).
    await page.getByTestId('accession-name-column-select').selectOption('Accession')

    // Select both trait columns
    await page.getByTestId('trait-checkbox-Yield_kg').check()
    await page.getByTestId('trait-checkbox-Moisture').check()

    // Rename Yield_kg → "Grain Yield <run_id>"
    const yieldLabel = page.getByTestId('trait-label-Yield_kg')
    await yieldLabel.clear()
    await yieldLabel.fill(YIELD_TRAIT)
    // Rename Moisture for uniqueness
    const moistureLabel = page.getByTestId('trait-label-Moisture')
    await moistureLabel.clear()
    await moistureLabel.fill(MOISTURE_TRAIT)

    // Add Notes as a free-form metadata column
    await page.getByTestId('metadata-add-select').selectOption('Notes')
    await page.getByTestId('metadata-add-button').click()
    await expect(page.getByTestId('metadata-label-Notes')).toHaveValue('Notes')

    // Go to sheet 2
    await page.getByTestId('sheet-next').click()
    await expect(page.getByText('Sheet 2 of 2:')).toBeVisible()
    await expect(page.getByText('Year2')).toBeVisible()

    // Verify carry-forward: plot columns, genotype, traits, and the Notes
    // metadata entry should all be carried forward by header match.
    await expect(page.getByTestId('plot-number-select')).toHaveValue('Plot')
    await expect(page.getByTestId('plot-row-select')).toHaveValue('Row')
    await expect(page.getByTestId('plot-col-select')).toHaveValue('Column')
    await expect(page.getByTestId('accession-name-column-select')).toHaveValue('Accession')
    await expect(page.getByTestId('trait-checkbox-Yield_kg')).toBeChecked()
    await expect(page.getByTestId('trait-checkbox-Moisture')).toBeChecked()
    await expect(page.getByTestId('trait-label-Yield_kg')).toHaveValue(YIELD_TRAIT)
    await expect(page.getByTestId('trait-label-Moisture')).toHaveValue(MOISTURE_TRAIT)
    await expect(page.getByTestId('metadata-label-Notes')).toHaveValue('Notes')

    // Continue is only enabled on the last sheet when all sheets are valid
    await page.getByTestId('mapping-continue').click()

    // ── Germplasm review ──
    // The fixture's Accession values (G001/G002/G003) are created as real
    // accessions in test setup, so every name resolves cleanly and we can
    // move on immediately.
    await expect(page.getByTestId('germplasm-review-continue')).toBeEnabled({ timeout: 30_000 })
    await page.getByTestId('germplasm-review-continue').click()

    // ── Upload + ingestion ──
    await expect(page.getByText('Creating Entities')).toBeVisible()
    await expect(page.getByTestId('upload-continue')).toBeEnabled({ timeout: 120_000 })

    // Verify progress panel showed both traits
    const progressPanel = page.getByTestId('ingestion-progress')
    await expect(progressPanel).toBeVisible()
    await expect(progressPanel).toContainText(YIELD_TRAIT)
    await expect(progressPanel).toContainText(MOISTURE_TRAIT)
    // Overall should be 12 records (3 rows × 2 traits × 2 sheets)
    await expect(progressPanel).toContainText('12 / 12 records')

    await page.getByTestId('upload-continue').click()
    await expect(page.getByTestId('confirm-heading')).toHaveText('Import Complete')

    // ── Verify via API ──
    const traitsRes = await page.request.get('/api/traits/all', { params: { limit: '500' } })
    const traits = await traitsRes.json()
    const yieldTrait = traits.find((t: { trait_name: string }) => t.trait_name === YIELD_TRAIT)
    const moistureTrait = traits.find((t: { trait_name: string }) => t.trait_name === MOISTURE_TRAIT)
    expect(yieldTrait).toBeTruthy()
    expect(moistureTrait).toBeTruthy()

    // Verify one Grain Yield record's record_info contains the genotype
    // (from the optional Accession column) and Notes (free-form metadata).
    // Use the /records/filter endpoint because it queries the base columnar
    // table directly, whereas /records queries a materialized view that may
    // lag behind bulk inserts. The endpoint streams NDJSON.
    const recordsRes = await page.request.get(
      `/api/traits/id/${yieldTrait.id}/records/filter`,
      { params: { experiment_names: MULTI_EXPERIMENT } },
    )
    const body = await recordsRes.text()
    const records = body
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .map((line) => JSON.parse(line) as { record_info?: Record<string, unknown> })
    expect(records.length).toBeGreaterThan(0)
    const first = records[0]
    expect(first.record_info).toBeTruthy()
    // Accession name came from the Accession column (G001/G002/G003 in fixture)
    expect(first.record_info?.accession_name).toMatch(/^G\d{3}$/)
    // Notes came from the metadata picker
    expect(first.record_info).toHaveProperty('Notes')
    // Sheet name is always included
    expect(first.record_info?.sheet).toMatch(/^Year[12]$/)

    // Cleanup
    await cleanupTestEntities(page.request, MULTI_RUN_ID)
    await cleanupTestEntities(page.request, 'E2E Multi')
  })
})

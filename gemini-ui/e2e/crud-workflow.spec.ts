import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'
import { cleanupTestEntities } from './helpers/cleanup'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

/**
 * End-to-end CRUD workflow test:
 * 1. Upload a minimal drone image dataset via the import wizard
 * 2. Fill out metadata in the wizard
 * 3. Verify dataset appears in the backend and UI
 * 4. Query/search for the dataset
 * 5. Rename the dataset
 * 6. Delete the dataset and verify full cleanup
 *
 * All data modifications go through the UI — no direct API seeding.
 */

const FIXTURES_DIR = path.join(__dirname, 'fixtures', 'test-drone-data')
const TEST_RUN_ID = `e2e-${Date.now()}`

// Unique names to avoid collisions with parallel runs or leftover data
const EXPERIMENT_NAME = `E2E Test Experiment ${TEST_RUN_ID}`
const SEASON_NAME = `E2E Test Season ${TEST_RUN_ID}`
const SITE_NAME = `E2E Test Site ${TEST_RUN_ID}`
const PLATFORM_NAME = `E2E Test Platform ${TEST_RUN_ID}`
const SENSOR_NAME = `E2E Test Sensor ${TEST_RUN_ID}`
const DATASET_NAME = `E2E Test Dataset ${TEST_RUN_ID}`
const RENAMED_DATASET = `Renamed Dataset ${TEST_RUN_ID}`

// Store IDs across steps
let datasetId: string
let experimentId: string

test.describe.serial('Dataset CRUD Workflow', () => {
  test.setTimeout(120_000)

  // Clean up any leftovers from previous failed runs
  test.beforeAll(async ({ request }) => {
    await cleanupTestEntities(request, 'E2E Test')
  })

  // ──────────────────────────────────────────────────────────────────
  // Helper: capture the initial dashboard counts so we can assert deltas
  // ──────────────────────────────────────────────────────────────────
  async function getDashboardCounts(page: import('@playwright/test').Page) {
    await page.goto('/')
    // Wait for at least one stat card to finish loading (no skeleton pulse)
    await page.waitForSelector('[data-testid^="stat-value-"]')
    // Give queries a moment to all resolve
    await page.waitForTimeout(1000)

    const counts: Record<string, number> = {}
    for (const key of ['experiments', 'datasets', 'sensors']) {
      const el = page.getByTestId(`stat-value-${key}`)
      const text = await el.textContent()
      counts[key] = parseInt(text ?? '0', 10)
    }
    return counts
  }

  // ──────────────────────────────────────────────────────────────────
  // Step 1 & 2: Upload dataset via import wizard
  // ──────────────────────────────────────────────────────────────────
  test('upload dataset via import wizard', async ({ page }) => {
    // Record pre-import counts
    const countsBefore = await getDashboardCounts(page)

    // Navigate to import page
    await page.goto('/import')
    await expect(page.getByRole('heading', { name: 'Import Data' })).toBeVisible()
    await expect(page.getByTestId('import-wizard')).toBeVisible()

    // ── Step 1: Detect ──
    // Upload test fixture files via the file input (simulating drag-drop)
    const fileInput = page.locator('[data-testid="dropzone"] input[type="file"]')
    await fileInput.setInputFiles([
      path.join(FIXTURES_DIR, '2024-01-15-TestFieldSubset', '2024-01-15_100MEDIA_DJI_0876.JPG'),
      path.join(FIXTURES_DIR, '2024-01-15-TestFieldSubset', '2024-01-15_100MEDIA_DJI_0877.JPG'),
      path.join(FIXTURES_DIR, '2024-01-15-TestFieldSubset', '2024-01-15_100MEDIA_DJI_0878.JPG'),
      path.join(FIXTURES_DIR, 'field_design.csv'),
    ])

    // Wait for detection to complete
    await expect(page.getByTestId('detection-summary')).toBeVisible({ timeout: 10_000 })

    // Verify detection found the right things
    await expect(page.getByText('4 files')).toBeVisible()
    await expect(page.getByText('CSV Files')).toBeVisible()
    await expect(page.getByText('field_design.csv')).toBeVisible()

    // Continue to metadata step
    await page.getByTestId('detect-continue').click()

    // ── Step 2: Metadata ──
    await expect(page.getByText('Configure Import Metadata')).toBeVisible()

    // Fill in all entity names — clear any pre-filled values first
    // Experiment
    const expInput = page.getByTestId('new-experiment')
    await expInput.clear()
    await expInput.fill(EXPERIMENT_NAME)

    // Season
    const seasonInput = page.getByTestId('new-season')
    await seasonInput.clear()
    await seasonInput.fill(SEASON_NAME)

    // Site
    const siteInput = page.getByTestId('new-site')
    await siteInput.clear()
    await siteInput.fill(SITE_NAME)

    // Sensor Platform
    const platformInput = page.getByTestId('new-sensor-platform')
    await platformInput.clear()
    await platformInput.fill(PLATFORM_NAME)

    // Sensor
    const sensorInput = page.getByTestId('new-sensor')
    await sensorInput.clear()
    await sensorInput.fill(SENSOR_NAME)

    // Dataset name
    const datasetInput = page.getByTestId('dataset-name-0')
    await datasetInput.clear()
    await datasetInput.fill(DATASET_NAME)

    // Continue to upload step
    await page.getByTestId('metadata-continue').click()

    // ── Step 3: Upload ──
    await expect(page.getByText('Creating Entities')).toBeVisible()

    // Wait for upload to complete — the Continue button becomes enabled
    await expect(page.getByTestId('upload-continue')).toBeEnabled({ timeout: 60_000 })

    // Continue to confirmation
    await page.getByTestId('upload-continue').click()

    // ── Step 4: Confirm ──
    await expect(page.getByTestId('confirm-heading')).toBeVisible()
    await expect(page.getByTestId('confirm-heading')).toHaveText('Import Complete')

    // Check created entities are listed (type and name are in separate spans)
    await expect(page.getByText(EXPERIMENT_NAME)).toBeVisible()
    await expect(page.getByText(DATASET_NAME)).toBeVisible()

    // Capture the experiment ID from the API (more reliable than navigating
    // through the UI, which can have React StrictMode timing issues)
    const expRes = await page.request.get('/api/experiments', {
      params: { experiment_name: EXPERIMENT_NAME },
    })
    const experiments = await expRes.json()
    const exp = experiments.find((e: { experiment_name: string }) => e.experiment_name === EXPERIMENT_NAME)
    expect(exp).toBeTruthy()
    experimentId = exp.id
  })

  // ──────────────────────────────────────────────────────────────────
  // Step 3: Verify dataset exists in backend and UI
  // ──────────────────────────────────────────────────────────────────
  test('verify dataset appears in backend and UI', async ({ page }) => {
    // 3a. Check via REST API that the dataset exists
    // The backend returns 404 for no search results, so use getAll and filter
    const allDatasetsRes = await page.request.get('/api/datasets/all', {
      params: { limit: '500', offset: '0' },
    })
    expect(allDatasetsRes.ok()).toBeTruthy()
    const allDatasets = await allDatasetsRes.json()
    const dataset = allDatasets.find((d: { dataset_name: string }) => d.dataset_name === DATASET_NAME)
    expect(dataset).toBeTruthy()
    datasetId = dataset.id

    // 3b. Check the experiment has the dataset in its associations
    const expDatasetsRes = await page.request.get(`/api/experiments/id/${experimentId}/datasets`)
    // May return 404 if no datasets are associated yet
    if (expDatasetsRes.ok()) {
      const expDatasets = await expDatasetsRes.json()
      const linked = expDatasets.find((d: { dataset_name: string }) => d.dataset_name === DATASET_NAME)
      expect(linked).toBeTruthy()
    }

    // 3c. Check dashboard counts increased
    const countsAfter = await getDashboardCounts(page)
    // At minimum, datasets count should have gone up
    // (We can't assert exact +1 because other tests might run, but it should be > 0)
    expect(countsAfter.datasets).toBeGreaterThan(0)
    expect(countsAfter.experiments).toBeGreaterThan(0)

    // 3d. Check dataset is accessible via its detail page and files are visible
    await page.goto(`/datasets/${datasetId}`)
    await expect(page.getByTestId('dataset-detail')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('heading', { name: DATASET_NAME })).toBeVisible()

    // Click the Files tab to verify uploaded files are listed
    await page.getByRole('tab', { name: 'Files' }).click()
    await expect(page.getByTestId('dataset-files')).toBeVisible({ timeout: 10_000 })

    // Verify the file count shows all 4 files
    await expect(page.getByTestId('file-count')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByTestId('file-count')).toContainText('4 files')

    // Verify image thumbnails are present (we uploaded 3 JPEGs)
    const thumbnails = page.getByTestId('image-thumbnail')
    await expect(thumbnails).toHaveCount(3, { timeout: 10_000 })

    // Verify thumbnails use the thumbnail endpoint (not full-res download)
    const firstThumbImg = thumbnails.first().locator('img')
    await expect(firstThumbImg).toHaveAttribute('src', /\/api\/files\/thumbnail\//)

    // Verify specific filenames are shown
    await expect(page.getByText('2024-01-15_100MEDIA_DJI_0876.JPG')).toBeVisible()
    await expect(page.getByText('2024-01-15_100MEDIA_DJI_0877.JPG')).toBeVisible()
    await expect(page.getByText('2024-01-15_100MEDIA_DJI_0878.JPG')).toBeVisible()

    // Verify the CSV file is listed in "Other Files"
    await expect(page.getByTestId('file-list')).toBeVisible()
    await expect(page.getByText('field_design.csv')).toBeVisible()

    // Verify clicking a thumbnail links to full-res download (not thumbnail)
    const thumbLink = thumbnails.first()
    await expect(thumbLink).toHaveAttribute('href', /\/api\/files\/download\//)

    // Verify files are accessible in MinIO via the paginated API
    const filesRes = await page.request.get(`/api/files/list_paginated/gemini/Raw/${encodeURIComponent(EXPERIMENT_NAME)}`, {
      params: { limit: '50', offset: '0' },
    })
    expect(filesRes.ok()).toBeTruthy()
    const filesData = await filesRes.json()
    expect(filesData.total_count).toBeGreaterThanOrEqual(4)
    expect(filesData.files.length).toBeGreaterThanOrEqual(4)

    // 3e. Check experiment detail page shows data and dataset
    await page.goto(`/experiments/${experimentId}`)
    await expect(page.getByRole('heading', { name: EXPERIMENT_NAME })).toBeVisible({ timeout: 15_000 })

    // Tab badge counts should load eagerly WITHOUT clicking each tab.
    // The import wizard created: 1 dataset, 1 season, 1 site, 1 sensor, 1 sensor platform.
    // Wait for queries to resolve, then check counts are non-zero.
    await expect(page.getByTestId('count-datasets')).not.toHaveText('0', { timeout: 10_000 })
    await expect(page.getByTestId('count-datasets')).toHaveText('1')
    await expect(page.getByTestId('count-seasons')).toHaveText('1')
    await expect(page.getByTestId('count-sites')).toHaveText('1')
    await expect(page.getByTestId('count-sensors')).toHaveText('1')

    // The default "Data" tab should show all files uploaded to this experiment
    await expect(page.getByTestId('experiment-files')).toBeVisible({ timeout: 10_000 })

    // Click the Datasets tab and verify the dataset card is shown
    await page.getByRole('tab', { name: /Datasets/ }).click()
    await expect(page.getByTestId('dataset-card')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(DATASET_NAME)).toBeVisible()

    // Expand the dataset card to see its files inline
    await page.getByTestId('dataset-card').click()
    await expect(page.getByTestId('dataset-files')).toBeVisible({ timeout: 10_000 })
  })

  // ──────────────────────────────────────────────────────────────────
  // Step 4: Query/search for the dataset
  // ──────────────────────────────────────────────────────────────────
  test('query dataset and verify files from UI', async ({ page }) => {
    // Navigate to the dataset detail page
    await page.goto(`/datasets/${datasetId}`)
    await expect(page.getByRole('heading', { name: DATASET_NAME })).toBeVisible({ timeout: 10_000 })

    // Switch to Files tab and verify content
    await page.getByRole('tab', { name: 'Files' }).click()
    await expect(page.getByTestId('dataset-files')).toBeVisible({ timeout: 10_000 })

    // Check file count text
    await expect(page.getByTestId('file-count')).toContainText('4 files')

    // Verify thumbnails use the thumbnail endpoint for efficient loading
    const firstImg = page.getByTestId('image-thumbnail').first().locator('img')
    await expect(firstImg).toHaveAttribute('src', /\/api\/files\/thumbnail\//)

    // Also verify via API that the dataset exists with the correct info
    const searchRes = await page.request.get(`/api/datasets/id/${datasetId}`)
    expect(searchRes.ok()).toBeTruthy()
    const result = await searchRes.json()
    expect(result.dataset_name).toBe(DATASET_NAME)
    // Verify the files_prefix was stored in dataset_info
    expect(result.dataset_info?.files_prefix).toBeTruthy()
  })

  // ──────────────────────────────────────────────────────────────────
  // Step 5: Rename the dataset via the UI
  // ──────────────────────────────────────────────────────────────────
  test('rename dataset via the UI', async ({ page }) => {
    // Navigate to the dataset detail page
    await page.goto(`/datasets/${datasetId}`)
    await expect(page.getByTestId('dataset-detail')).toBeVisible({ timeout: 10_000 })
    await expect(page.getByRole('heading', { name: DATASET_NAME })).toBeVisible()

    // Click Edit
    await page.getByTestId('edit-btn').click()

    // The form should appear with the current name pre-filled
    const nameInput = page.locator('input#dataset_name')
    await expect(nameInput).toBeVisible()
    await expect(nameInput).toHaveValue(DATASET_NAME)

    // Clear and type the new name
    await nameInput.clear()
    await nameInput.fill(RENAMED_DATASET)

    // Save
    await page.getByRole('button', { name: 'Save' }).click()

    // Wait for the save to complete and form to close
    await expect(page.getByTestId('dataset-detail')).toBeVisible({ timeout: 10_000 })

    // Verify the new name is shown in the detail view
    await expect(page.getByRole('heading', { name: RENAMED_DATASET })).toBeVisible()
    // Old name should be gone from the heading
    await expect(page.getByRole('heading', { name: DATASET_NAME })).not.toBeVisible()

    // Verify on the backend
    const apiRes = await page.request.get(`/api/datasets/id/${datasetId}`)
    expect(apiRes.ok()).toBeTruthy()
    const updated = await apiRes.json()
    expect(updated.dataset_name).toBe(RENAMED_DATASET)
  })

  // ──────────────────────────────────────────────────────────────────
  // Step 6: Delete and verify full cleanup
  // ──────────────────────────────────────────────────────────────────
  test('delete dataset and verify cleanup', async ({ page }) => {
    // Record counts before deletion
    const countsBefore = await getDashboardCounts(page)

    // Navigate to the dataset detail
    await page.goto(`/datasets/${datasetId}`)
    await expect(page.getByRole('heading', { name: RENAMED_DATASET })).toBeVisible({ timeout: 10_000 })

    // Click Delete
    await page.getByTestId('delete-btn').click()

    // Confirmation dialog should appear
    await expect(page.getByText(`Are you sure you want to delete ${RENAMED_DATASET}?`)).toBeVisible()

    // Confirm deletion
    await page.getByTestId('confirm-delete').click()

    // Should redirect to datasets list
    await page.waitForURL('/datasets')

    // 6a. Verify the dataset no longer appears in the list
    // Wait for the table to load
    await page.waitForTimeout(1000)
    // The renamed dataset should not be in any table cell
    await expect(page.getByRole('cell', { name: RENAMED_DATASET })).not.toBeVisible()

    // 6b. Verify backend returns 404 for the deleted dataset
    const apiRes = await page.request.get(`/api/datasets/id/${datasetId}`)
    // The backend might return 404 or 500 for missing entities
    expect(apiRes.ok()).toBeFalsy()

    // 6c. Verify the dataset is gone from API
    const searchRes = await page.request.get(`/api/datasets/id/${datasetId}`)
    expect(searchRes.ok()).toBeFalsy()

    // 6d. Verify the experiment's datasets tab count updated and dataset is gone
    await page.goto(`/experiments/${experimentId}`)
    await expect(page.getByRole('heading', { name: EXPERIMENT_NAME })).toBeVisible({ timeout: 15_000 })
    // The datasets count badge should show 0 (loaded eagerly, no click needed)
    await expect(page.getByTestId('count-datasets')).toHaveText('0', { timeout: 10_000 })
    // Verify clicking Datasets tab shows no dataset cards
    await page.getByRole('tab', { name: /Datasets/ }).click()
    await page.waitForTimeout(1000)
    await expect(page.getByText(RENAMED_DATASET)).not.toBeVisible()

    // 6e. Dashboard dataset count should have decreased
    const countsAfter = await getDashboardCounts(page)
    expect(countsAfter.datasets).toBeLessThan(countsBefore.datasets)

    // ── Cleanup: delete ALL entities created by this test run ──
    await cleanupTestEntities(page.request, TEST_RUN_ID)
  })
})

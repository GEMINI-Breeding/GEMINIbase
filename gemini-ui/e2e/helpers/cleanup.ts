import type { APIRequestContext } from '@playwright/test'

/**
 * Deletes all entities whose names contain the given substring.
 * Cleans up in dependency order: records-bearing entities first, then parent entities.
 */
export async function cleanupTestEntities(request: APIRequestContext, nameContains: string) {
  // Order matters: delete leaf entities before parent entities to avoid FK
  // issues. Deleting a GenotypingStudy cascades to its genotype_records and
  // any variants with no remaining study references; that's why variants
  // don't need a dedicated entry here. Populations are deleted after plot
  // cascade (via experiment delete) so the accession/line sweep at the tail
  // isn't blocked by population_accessions FKs.
  const entityTypes = [
    { endpoint: 'datasets', nameField: 'dataset_name' },
    { endpoint: 'sensors', nameField: 'sensor_name' },
    { endpoint: 'sensor_platforms', nameField: 'sensor_platform_name' },
    { endpoint: 'traits', nameField: 'trait_name' },
    { endpoint: 'genotyping_studies', nameField: 'study_name' },
    { endpoint: 'sites', nameField: 'site_name' },
    { endpoint: 'seasons', nameField: 'season_name' },
    { endpoint: 'populations', nameField: 'population_name' },
    { endpoint: 'experiments', nameField: 'experiment_name' },
    { endpoint: 'accessions', nameField: 'accession_name' },
    { endpoint: 'lines', nameField: 'line_name' },
    { endpoint: 'variants', nameField: 'variant_name' },
  ]

  for (const { endpoint, nameField } of entityTypes) {
    try {
      const res = await request.get(`/api/${endpoint}/all`, { params: { limit: '500' } })
      if (!res.ok()) continue
      const items = await res.json()
      if (!Array.isArray(items)) continue

      for (const item of items) {
        const name = item[nameField] || ''
        if (name.includes(nameContains)) {
          try {
            await request.delete(`/api/${endpoint}/id/${item.id}`)
          } catch {
            // Ignore individual delete failures
          }
        }
      }
    } catch {
      // Ignore fetch failures (e.g., 404 for empty lists)
    }
  }
}

import type { APIRequestContext } from '@playwright/test'

/**
 * Deletes all entities whose names contain the given substring.
 * Cleans up in dependency order: records-bearing entities first, then parent entities.
 */
export async function cleanupTestEntities(request: APIRequestContext, nameContains: string) {
  // Order matters: delete leaf entities before parent entities to avoid FK issues
  const entityTypes = [
    { endpoint: 'datasets', nameField: 'dataset_name' },
    { endpoint: 'sensors', nameField: 'sensor_name' },
    { endpoint: 'sensor_platforms', nameField: 'sensor_platform_name' },
    { endpoint: 'traits', nameField: 'trait_name' },
    { endpoint: 'sites', nameField: 'site_name' },
    { endpoint: 'seasons', nameField: 'season_name' },
    { endpoint: 'populations', nameField: 'population_name' },
    { endpoint: 'experiments', nameField: 'experiment_name' },
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

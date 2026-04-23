import { post } from '@/api/client'
import type { GwasSubmitInput, JobOutput } from '@/api/types'

export const gwasApi = {
  /**
   * Submit one or more RUN_GWAS jobs.
   * - `model` = "lmm" or "bslmm" + `trait_id`   → 1 job.
   * - `model` = "lmm" or "bslmm" + `trait_ids`  → N jobs (one per trait).
   * - `model` = "mvlmm" + `trait_ids` (len ≥ 2) → 1 multivariate job.
   */
  submit: (data: GwasSubmitInput) =>
    post<JobOutput[]>('api/gwas/submit', data),
}

import { createFileRoute } from '@tanstack/react-router'
import { PageHeader } from '@/components/layout/page-header'
import { WizardShell } from '@/components/import-wizard/wizard-shell'

export const Route = createFileRoute('/import/')({
  component: ImportPage,
})

function ImportPage() {
  return (
    <div>
      <PageHeader title="Import Data" description="Upload and import datasets into GEMINI" />
      <WizardShell />
    </div>
  )
}

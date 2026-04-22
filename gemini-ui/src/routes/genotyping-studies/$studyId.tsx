import { useState } from 'react'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  Pencil,
  Trash2,
  Upload,
  Download,
  Loader2,
  ChevronDown,
} from 'lucide-react'
import { useGenotypingStudies } from '@/hooks/use-entity-hooks'
import { EntityForm, type FieldDef } from '@/components/crud/entity-form'
import { DeleteDialog } from '@/components/crud/delete-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table'
import { genotypingStudiesApi } from '@/api/endpoints/genotyping-studies'

const fields: FieldDef[] = [
  { name: 'study_name', label: 'Name', type: 'text', required: true },
  { name: 'study_info', label: 'Info (JSON)', type: 'json' },
]

const EXPORT_FORMATS: { value: string; label: string; ext: string }[] = [
  { value: 'hapmap', label: 'HapMap', ext: 'hmp.txt' },
  { value: 'vcf', label: 'VCF', ext: 'vcf' },
  { value: 'numeric', label: 'Numeric matrix', ext: 'num.txt' },
  { value: 'plink', label: 'PLINK', ext: 'ped' },
]

const RECORDS_PAGE_SIZE = 50

function GenotypingStudyDetail() {
  const { studyId } = Route.useParams()
  const navigate = useNavigate()
  const { data: study, isLoading } = useGenotypingStudies.useGetById(studyId)
  const updateMutation = useGenotypingStudies.useUpdate()
  const removeMutation = useGenotypingStudies.useRemove()
  const [editing, setEditing] = useState(false)
  const [showDelete, setShowDelete] = useState(false)
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const [exporting, setExporting] = useState<string | null>(null)
  const [recordsOffset, setRecordsOffset] = useState(0)

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ['genotyping-study-records', studyId, recordsOffset],
    queryFn: () => genotypingStudiesApi.getRecords(studyId, RECORDS_PAGE_SIZE, recordsOffset),
  })

  async function handleExport(format: string, ext: string) {
    if (!study?.study_name) return
    setExportMenuOpen(false)
    setExporting(format)
    try {
      const blob = await genotypingStudiesApi.exportBlob(studyId, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${study.study_name}.${ext}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed', err)
    } finally {
      setExporting(null)
    }
  }

  if (isLoading) return <div className="animate-pulse p-8">Loading...</div>
  if (!study) return <div className="p-8">Genotyping Study not found</div>

  return (
    <div>
      <PageHeader
        title={study.study_name ?? 'Genotyping Study'}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate({ to: '/genotyping-studies' })}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Back
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate({ to: '/import' })}
              data-testid="study-import-data"
            >
              <Upload className="mr-2 h-4 w-4" /> Import Data
            </Button>
            <div className="relative">
              <Button
                variant="outline"
                onClick={() => setExportMenuOpen(!exportMenuOpen)}
                disabled={exporting !== null}
                data-testid="study-export-menu"
              >
                {exporting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Export
                <ChevronDown className="ml-1 h-4 w-4" />
              </Button>
              {exportMenuOpen && (
                <div className="absolute right-0 mt-1 w-44 rounded-md border bg-popover shadow-md z-10">
                  {EXPORT_FORMATS.map((f) => (
                    <button
                      key={f.value}
                      type="button"
                      className="w-full text-left px-3 py-2 text-sm hover:bg-muted"
                      onClick={() => handleExport(f.value, f.ext)}
                      data-testid={`study-export-${f.value}`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <Button variant="outline" onClick={() => setEditing(!editing)}>
              <Pencil className="mr-2 h-4 w-4" /> Edit
            </Button>
            <Button variant="destructive" onClick={() => setShowDelete(true)}>
              <Trash2 className="mr-2 h-4 w-4" /> Delete
            </Button>
          </div>
        }
      />
      {editing ? (
        <EntityForm
          fields={fields}
          defaultValues={study}
          onSubmit={(data) =>
            updateMutation.mutate(
              { id: studyId, data: data as never },
              { onSuccess: () => setEditing(false) },
            )
          }
          onCancel={() => setEditing(false)}
          isLoading={updateMutation.isPending}
        />
      ) : (
        <Tabs defaultValue="overview" className="space-y-4">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="records" data-testid="tab-records">Records</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 rounded-md border p-4">
                <div>
                  <p className="text-sm text-muted-foreground">Name</p>
                  <p>{study.study_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">ID</p>
                  <p className="font-mono text-xs">{study.id}</p>
                </div>
              </div>
              {study.study_info && Object.keys(study.study_info).length > 0 && (
                <div className="rounded-md border p-4">
                  <h3 className="text-sm font-medium mb-2">Info</h3>
                  <pre className="text-xs font-mono whitespace-pre-wrap">{JSON.stringify(study.study_info, null, 2)}</pre>
                </div>
              )}
            </div>
          </TabsContent>
          <TabsContent value="records">
            <div className="rounded-md border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Variant</TableHead>
                    <TableHead>Chrom</TableHead>
                    <TableHead>Position</TableHead>
                    <TableHead>Accession</TableHead>
                    <TableHead>Call</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recordsLoading && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-6">
                        <Loader2 className="inline w-4 h-4 animate-spin mr-2" /> Loading records...
                      </TableCell>
                    </TableRow>
                  )}
                  {!recordsLoading && (!records || records.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-6">
                        No records yet. Use <strong>Import Data</strong> above to upload a matrix.
                      </TableCell>
                    </TableRow>
                  )}
                  {!recordsLoading &&
                    records?.map((r) => (
                      <TableRow key={r.id}>
                        <TableCell className="font-mono text-xs">{r.variant_name}</TableCell>
                        <TableCell>{r.chromosome ?? '—'}</TableCell>
                        <TableCell>{r.position ?? '—'}</TableCell>
                        <TableCell className="text-xs">{r.accession_name}</TableCell>
                        <TableCell className="font-mono">{r.call_value}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
            <div className="flex items-center justify-between mt-3">
              <p className="text-xs text-muted-foreground">
                Showing {records?.length ?? 0} record{records?.length === 1 ? '' : 's'} starting at offset {recordsOffset}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={recordsOffset === 0}
                  onClick={() => setRecordsOffset(Math.max(0, recordsOffset - RECORDS_PAGE_SIZE))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={(records?.length ?? 0) < RECORDS_PAGE_SIZE}
                  onClick={() => setRecordsOffset(recordsOffset + RECORDS_PAGE_SIZE)}
                >
                  Next
                </Button>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      )}
      <DeleteDialog
        open={showDelete}
        onClose={() => setShowDelete(false)}
        onConfirm={() =>
          removeMutation.mutate(studyId, {
            onSuccess: () => navigate({ to: '/genotyping-studies' }),
          })
        }
        entityName={study.study_name ?? 'Genotyping Study'}
        isLoading={removeMutation.isPending}
      />
    </div>
  )
}

export const Route = createFileRoute('/genotyping-studies/$studyId')({ component: GenotypingStudyDetail })

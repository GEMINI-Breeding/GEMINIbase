import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

interface DeleteDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  entityName: string
  description?: string
  isLoading?: boolean
}

export function DeleteDialog({
  open,
  onClose,
  onConfirm,
  entityName,
  description,
  isLoading,
}: DeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent onClose={onClose}>
        <DialogHeader>
          <DialogTitle>Delete {entityName}</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete {entityName}? This action cannot be
            undone.
            {description && <><br />{description}</>}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose} data-testid="cancel-delete">
            Cancel
          </Button>
          <Button variant="destructive" onClick={onConfirm} disabled={isLoading} data-testid="confirm-delete">
            {isLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

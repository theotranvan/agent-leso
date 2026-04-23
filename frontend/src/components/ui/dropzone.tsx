'use client';
import { useCallback, useState } from 'react';
import { Upload, FileIcon, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface DropzoneProps {
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  label?: string;
  hint?: string;
  onFilesSelected: (files: File[]) => Promise<void> | void;
  currentFileName?: string;
  uploading?: boolean;
  disabled?: boolean;
  className?: string;
}

export function Dropzone({
  accept,
  multiple = false,
  maxSizeMB = 25,
  label,
  hint,
  onFilesSelected,
  currentFileName,
  uploading = false,
  disabled = false,
  className,
}: DropzoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled || uploading) return;
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, [disabled, uploading]);

  const validateAndSubmit = useCallback(async (files: File[]) => {
    setLocalError(null);
    for (const f of files) {
      if (f.size / 1024 / 1024 > maxSizeMB) {
        setLocalError(`${f.name} dépasse ${maxSizeMB} Mo`);
        return;
      }
    }
    try {
      await onFilesSelected(files);
    } catch (e: any) {
      setLocalError(e?.message || 'Upload échoué');
    }
  }, [maxSizeMB, onFilesSelected]);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (disabled || uploading) return;
    const files = Array.from(e.dataTransfer.files);
    if (!files.length) return;
    await validateAndSubmit(multiple ? files : [files[0]]);
  }, [disabled, uploading, multiple, validateAndSubmit]);

  const handleInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    await validateAndSubmit(multiple ? files : [files[0]]);
    e.target.value = '';
  }, [multiple, validateAndSubmit]);

  return (
    <div className={className}>
      <label
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={cn(
          'relative flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center cursor-pointer transition-colors',
          dragActive && 'dropzone-active',
          !dragActive && !currentFileName && 'border-muted-foreground/30 hover:border-muted-foreground/50 bg-muted/30',
          currentFileName && 'border-emerald-300 bg-emerald-50/50',
          disabled && 'opacity-60 cursor-not-allowed',
        )}
      >
        <input
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled || uploading}
          onChange={handleInput}
          className="sr-only"
        />
        {uploading ? (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Téléversement en cours…</p>
          </>
        ) : currentFileName ? (
          <>
            <FileIcon className="h-6 w-6 text-emerald-700" />
            <p className="text-sm font-medium text-emerald-900">{currentFileName}</p>
            <p className="text-xs text-muted-foreground">Clique pour remplacer</p>
          </>
        ) : (
          <>
            <Upload className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm font-medium">{label || 'Glisse un fichier ici'}</p>
            {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
            <p className="text-xs text-muted-foreground">
              ou clique pour choisir {accept ? `(${accept})` : ''}
            </p>
          </>
        )}
      </label>
      {localError && (
        <p className="mt-2 text-xs text-red-600 flex items-center gap-1">
          <X className="h-3 w-3" /> {localError}
        </p>
      )}
    </div>
  );
}

'use client';
import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, CheckCircle2, XCircle, FileText } from 'lucide-react';
import { api } from '@/lib/api';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface DocumentUploaderProps {
  projectId?: string;
  onUploaded?: (doc: any) => void;
}

interface UploadItem {
  id: string;
  file: File;
  progress: number;
  status: 'uploading' | 'done' | 'error';
  error?: string;
  documentId?: string;
}

export function DocumentUploader({ projectId, onUploaded }: DocumentUploaderProps) {
  const [items, setItems] = useState<UploadItem[]>([]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        const id = Math.random().toString(36).slice(2);
        setItems((prev) => [...prev, { id, file, progress: 0, status: 'uploading' }]);

        try {
          const doc = await api.uploadDocument(file, projectId, (pct) => {
            setItems((prev) => prev.map((it) => (it.id === id ? { ...it, progress: pct } : it)));
          });
          setItems((prev) =>
            prev.map((it) => (it.id === id ? { ...it, progress: 100, status: 'done', documentId: doc.id } : it)),
          );
          onUploaded?.(doc);
        } catch (e: any) {
          setItems((prev) =>
            prev.map((it) => (it.id === id ? { ...it, status: 'error', error: e.message } : it)),
          );
        }
      }
    },
    [projectId, onUploaded],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/octet-stream': ['.ifc', '.bcf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
    },
    maxSize: 100 * 1024 * 1024, // 100 MB
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
          isDragActive ? 'border-primary bg-accent' : 'border-muted-foreground/25 hover:border-primary/50',
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-10 w-10 text-muted-foreground mb-2" />
        <p className="text-sm font-medium">
          {isDragActive ? 'Déposez ici...' : 'Glissez-déposez vos fichiers ou cliquez pour parcourir'}
        </p>
        <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, IFC, BCF, XLSX, PNG, JPEG (max 100 MB)</p>
      </div>

      {items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="border rounded-md p-3 text-sm">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                <span className="flex-1 truncate">{item.file.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(item.file.size / 1024 / 1024).toFixed(1)} MB
                </span>
                {item.status === 'done' && <CheckCircle2 className="h-4 w-4 text-emerald-600" />}
                {item.status === 'error' && <XCircle className="h-4 w-4 text-red-600" />}
              </div>
              {item.status === 'uploading' && <Progress value={item.progress} className="mt-2" />}
              {item.status === 'error' && (
                <p className="text-xs text-red-600 mt-1">{item.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

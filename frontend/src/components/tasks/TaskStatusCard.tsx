'use client';
import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle, Loader2, Download, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { STATUS_LABELS } from '@/lib/utils';

interface Props {
  taskId: string;
  pollInterval?: number;
}

export function TaskStatusCard({ taskId, pollInterval = 3000 }: Props) {
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const data = await api.getTaskStatus(taskId);
      setStatus(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(() => {
      fetchStatus();
    }, pollInterval);
    return () => clearInterval(interval);
  }, [taskId, pollInterval]);

  // Stop polling when done
  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'failed') {
      // noop - laisse le polling tourner mais en vrai on pourrait clear ici
    }
  }, [status]);

  const handleRetry = async () => {
    try {
      await api.retryTask(taskId);
      fetchStatus();
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (error) return <div className="text-sm text-destructive">{error}</div>;
  if (!status) return <div className="text-sm text-muted-foreground">Chargement...</div>;

  const st = STATUS_LABELS[status.status];

  return (
    <div className="border rounded-lg p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {status.status === 'running' && <Loader2 className="h-5 w-5 animate-spin text-blue-600" />}
          {status.status === 'pending' && <Loader2 className="h-5 w-5 animate-spin text-slate-500" />}
          {status.status === 'completed' && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
          {status.status === 'failed' && <XCircle className="h-5 w-5 text-red-600" />}
          <Badge className={st.color}>{st.label}</Badge>
        </div>
        {status.status === 'failed' && (
          <Button size="sm" variant="outline" onClick={handleRetry}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Relancer
          </Button>
        )}
      </div>

      {(status.status === 'pending' || status.status === 'running') && (
        <Progress value={status.progress || (status.status === 'running' ? 50 : 5)} />
      )}

      {status.error_message && (
        <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-900">
          {status.error_message}
        </div>
      )}

      {status.result_preview && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-2">Aperçu</p>
          <div className="rounded-md bg-muted p-3 text-sm whitespace-pre-wrap max-h-96 overflow-y-auto">
            {status.result_preview}
          </div>
        </div>
      )}

      {status.result_url && (
        <Button asChild>
          <a href={status.result_url} target="_blank" rel="noopener noreferrer" download>
            <Download className="h-4 w-4 mr-2" />
            Télécharger le document
          </a>
        </Button>
      )}
    </div>
  );
}

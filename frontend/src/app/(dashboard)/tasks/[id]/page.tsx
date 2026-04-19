'use client';
import { useEffect, useState } from 'react';
import { use } from 'react';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TaskStatusCard } from '@/components/tasks/TaskStatusCard';
import { TASK_TYPE_LABELS, formatDateTime } from '@/lib/utils';

export default function TaskDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [task, setTask] = useState<any>(null);

  useEffect(() => {
    api.getTask(id).then(setTask);
    // Refresh task data every 3s aussi pour récupérer model_used / cost / tokens
    const i = setInterval(() => {
      api.getTask(id).then(setTask).catch(() => {});
    }, 3000);
    return () => clearInterval(i);
  }, [id]);

  if (!task) return <div className="text-muted-foreground">Chargement...</div>;

  return (
    <div className="space-y-6 max-w-4xl">
      <Link href="/dashboard" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Retour
      </Link>
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{TASK_TYPE_LABELS[task.task_type] || task.task_type}</h1>
        <p className="text-sm text-muted-foreground mt-1">Créée le {formatDateTime(task.created_at)}</p>
      </div>

      <TaskStatusCard taskId={id} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle className="text-sm">Modèle utilisé</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm font-mono">{task.model_used || '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">Tokens consommés</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm">{task.tokens_used?.toLocaleString('fr-FR') || '0'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-sm">Coût estimé</CardTitle></CardHeader>
          <CardContent>
            <p className="text-sm">{task.cost_euros ? `${Number(task.cost_euros).toFixed(4)} €` : '—'}</p>
          </CardContent>
        </Card>
      </div>

      {task.input_params && Object.keys(task.input_params).length > 0 && (
        <Card>
          <CardHeader><CardTitle>Paramètres</CardTitle></CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-64">
              {JSON.stringify(task.input_params, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { use } from 'react';
import { ArrowLeft, FileText, Sparkles, MapPin, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DocumentUploader } from '@/components/dashboard/DocumentUploader';
import { STATUS_LABELS, TASK_TYPE_LABELS, formatDate, formatDateTime, LOT_LABELS } from '@/lib/utils';

export default function ProjectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [project, setProject] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    const [p, d, t] = await Promise.all([
      api.getProject(id),
      api.listProjectDocuments(id),
      api.listProjectTasks(id),
    ]);
    setProject(p);
    setDocuments(d.documents);
    setTasks(t.tasks);
    setLoading(false);
  };

  useEffect(() => {
    fetchAll();
  }, [id]);

  const handleDeleteDoc = async (docId: string) => {
    if (!confirm('Supprimer ce document ?')) return;
    await api.deleteDocument(docId);
    fetchAll();
  };

  if (loading) return <div className="text-muted-foreground">Chargement...</div>;
  if (!project) return <div>Projet introuvable</div>;

  return (
    <div className="space-y-6">
      <Link href="/projects" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Retour aux projets
      </Link>

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
          {project.type_ouvrage && <p className="text-sm text-muted-foreground mt-1">{project.type_ouvrage}</p>}
          {project.address && (
            <p className="text-sm text-muted-foreground mt-1 flex items-center gap-1">
              <MapPin className="h-3 w-3" /> {project.address}
            </p>
          )}
          {project.lots?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {project.lots.map((lot: string) => (
                <Badge key={lot} variant="secondary">{LOT_LABELS[lot] || lot}</Badge>
              ))}
            </div>
          )}
        </div>
        <Button asChild>
          <Link href={`/tasks/new?project_id=${id}`}>
            <Sparkles className="h-4 w-4 mr-2" />
            Nouvelle tâche
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Documents ({documents.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <DocumentUploader projectId={id} onUploaded={fetchAll} />

            {documents.length > 0 && (
              <ul className="divide-y border rounded-md">
                {documents.map((d) => (
                  <li key={d.id} className="p-3 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{d.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {d.file_type.toUpperCase()} · {formatDate(d.created_at)}
                        {!d.processed && ' · Traitement en cours'}
                        {d.page_count && ` · ${d.page_count} pages`}
                      </p>
                    </div>
                    <Button size="icon" variant="ghost" onClick={() => handleDeleteDoc(d.id)}>
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Tâches ({tasks.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {tasks.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucune tâche pour ce projet</p>
            ) : (
              <ul className="divide-y">
                {tasks.map((t) => {
                  const st = STATUS_LABELS[t.status];
                  return (
                    <li key={t.id} className="py-3 first:pt-0 last:pb-0">
                      <Link href={`/tasks/${t.id}`} className="flex items-center justify-between hover:bg-accent -mx-2 px-2 rounded-md transition-colors">
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{TASK_TYPE_LABELS[t.task_type] || t.task_type}</p>
                          <p className="text-xs text-muted-foreground">{formatDateTime(t.created_at)}</p>
                        </div>
                        <Badge className={st.color}>{st.label}</Badge>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

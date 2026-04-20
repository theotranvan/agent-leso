'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, FolderKanban } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { formatDate, LOT_LABELS } from '@/lib/utils';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '',
    type_ouvrage: '',
    address: '',
    lots: [] as string[],
  });

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await api.listProjects();
      setProjects(data.projects);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.createProject(form);
      setShowForm(false);
      setForm({ name: '', type_ouvrage: '', address: '', lots: [] });
      await fetchProjects();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleLot = (lot: string) => {
    setForm((f) => ({
      ...f,
      lots: f.lots.includes(lot) ? f.lots.filter((l) => l !== lot) : [...f.lots, lot],
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projets</h1>
          <p className="text-sm text-muted-foreground mt-1">Gérez vos opérations et leurs documents techniques</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau projet
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Nom du projet *</Label>
                  <Input
                    id="name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type_ouvrage">Type d'ouvrage</Label>
                  <Input
                    id="type_ouvrage"
                    placeholder="Logement, bureau, ERP..."
                    value={form.type_ouvrage}
                    onChange={(e) => setForm({ ...form, type_ouvrage: e.target.value })}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="address">Adresse</Label>
                <Input
                  id="address"
                  value={form.address}
                  onChange={(e) => setForm({ ...form, address: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Lots concernés</Label>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(LOT_LABELS).map(([key, label]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => toggleLot(key)}
                      className={`text-xs px-3 py-1.5 rounded-md border transition-colors ${
                        form.lots.includes(key)
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-background hover:bg-accent'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              {error && <div className="text-sm text-destructive">{error}</div>}
              <div className="flex gap-2">
                <Button type="submit" disabled={submitting}>
                  {submitting ? 'Création...' : 'Créer le projet'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Annuler</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="text-muted-foreground">Chargement...</div>
      ) : projects.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FolderKanban className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
            <p className="text-sm font-medium">Aucun projet</p>
            <p className="text-xs text-muted-foreground mt-1">Créez votre premier projet pour commencer</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`}>
              <Card className="hover:border-primary transition-colors cursor-pointer h-full">
                <CardContent className="pt-6">
                  <h3 className="font-medium truncate">{p.name}</h3>
                  {p.type_ouvrage && <p className="text-xs text-muted-foreground mt-1">{p.type_ouvrage}</p>}
                  {p.address && <p className="text-xs text-muted-foreground mt-1 truncate">{p.address}</p>}
                  {p.lots?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-3">
                      {p.lots.slice(0, 4).map((lot: string) => (
                        <Badge key={lot} variant="secondary" className="text-[10px]">{LOT_LABELS[lot] || lot}</Badge>
                      ))}
                      {p.lots.length > 4 && <Badge variant="outline" className="text-[10px]">+{p.lots.length - 4}</Badge>}
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground mt-3">Créé le {formatDate(p.created_at)}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

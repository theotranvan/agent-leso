'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Plus, Flame } from 'lucide-react';
import { api } from '@/lib/api';
import { CANTONS_ROMANDS, AFFECTATIONS_SIA, OPERATION_TYPES, STANDARDS_ENERGETIQUES } from '@/lib/ch';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CantonPicker } from '@/components/swiss/CantonPicker';
import { StatusBadge } from '@/components/swiss/StatusBadge';

export default function ThermiquePage() {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({
    name: '',
    canton: 'GE',
    affectation: 'logement_collectif',
    operation_type: 'neuf',
    standard: 'sia_380_1',
    zones: [],
    walls: [],
    openings: [],
    thermal_bridges: [],
    systems: {},
    hypotheses: {},
  });
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await api.thermique.listModels();
      setModels(data.models);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const created = await api.thermique.createModel(form);
      setShowForm(false);
      setForm({ ...form, name: '' });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Flame className="h-6 w-6" />
            Thermique SIA 380/1
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Pipeline thermique suisse : saisie → fichier Lesosai → justificatif officiel
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau modèle
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle>Nouveau modèle thermique</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nom du modèle *</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="space-y-2">
                  <Label>Canton *</Label>
                  <CantonPicker value={form.canton} onChange={(c) => setForm({ ...form, canton: c })} />
                </div>
                <div className="space-y-2">
                  <Label>Affectation</Label>
                  <Select value={form.affectation} onValueChange={(v) => setForm({ ...form, affectation: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {AFFECTATIONS_SIA.map((a) => (
                        <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Opération</Label>
                  <Select value={form.operation_type} onValueChange={(v) => setForm({ ...form, operation_type: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {OPERATION_TYPES.map((o) => (
                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label>Standard énergétique visé</Label>
                  <Select value={form.standard} onValueChange={(v) => setForm({ ...form, standard: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {STANDARDS_ENERGETIQUES.map((s) => (
                        <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Les zones, parois et ouvertures se complètent dans l'écran détail du modèle. Un squelette vide sera créé.
              </p>
              {error && <div className="text-sm text-destructive">{error}</div>}
              <div className="flex gap-2">
                <Button type="submit">Créer</Button>
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Annuler</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="text-muted-foreground">Chargement...</div>
      ) : models.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            <Flame className="h-10 w-10 mx-auto mb-2 text-muted-foreground" />
            Aucun modèle thermique. Créez votre premier modèle.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m) => (
            <Link key={m.id} href={`/thermique/${m.id}`}>
              <Card className="hover:border-primary transition-colors cursor-pointer h-full">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium truncate">{m.name}</h3>
                    <StatusBadge status={m.status === 'completed' ? 'CONFORME' : m.status === 'draft' ? 'A_VERIFIER' : 'INFO'} label={m.status} />
                  </div>
                  <p className="text-xs text-muted-foreground">{m.canton} · {m.affectation} · {m.operation_type}</p>
                  <p className="text-xs text-muted-foreground mt-1">{m.standard}</p>
                  <p className="text-xs text-muted-foreground mt-3">Créé le {formatDate(m.created_at)}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

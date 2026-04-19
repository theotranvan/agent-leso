'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Building, Plus, Zap } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatDate } from '@/lib/utils';
import { StatusBadge } from '@/components/swiss/StatusBadge';

export default function StructurePage() {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: '',
    referentiel: 'sia',
    exposure_class: 'XC2',
    consequence_class: 'CC2',
    seismic_zone: 'Z1b',
  });
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const d = await api.structure.listModels();
      setModels(d.models);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.structure.createModel({
        name: form.name,
        project: {
          name: form.name,
          referentiel: form.referentiel,
          exposure_class: form.exposure_class,
          consequence_class: form.consequence_class,
          seismic_zone: form.seismic_zone,
        },
        nodes: [],
        members: [],
        supports: [],
        load_cases: [],
        combinations: [],
      });
      setShowForm(false);
      setForm({ ...form, name: '' });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Building className="h-6 w-6" />
            Structure SIA 260-267
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Génération SAF · import résultats · double-check analytique · note de calcul
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Nouveau modèle
        </Button>
      </div>

      <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
        <strong>⚠ Responsabilité ingénieur :</strong> la note de calcul finale n'est générée qu'après
        validation explicite du modèle et des résultats par un ingénieur. L'agent prépare, vérifie
        et formalise — il ne signe jamais à votre place.
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Nouveau modèle structurel</CardTitle>
            <CardDescription>
              Le modèle sera enrichi ensuite par import BIM ou définition manuelle.
              Le SAF généré est compatible Scia Engineer, RFEM/RSTAB.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nom *</Label>
                  <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div className="space-y-2">
                  <Label>Référentiel</Label>
                  <Select value={form.referentiel} onValueChange={(v) => setForm({ ...form, referentiel: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sia">SIA 260-267 (Suisse)</SelectItem>
                      <SelectItem value="eurocode">Eurocodes</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Classe d'exposition SIA 262</Label>
                  <Select value={form.exposure_class} onValueChange={(v) => setForm({ ...form, exposure_class: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {['XC1', 'XC2', 'XC3', 'XC4', 'XD1', 'XD2', 'XD3', 'XF1', 'XF2', 'XF3', 'XF4'].map((c) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Classe de conséquence SIA 260</Label>
                  <Select value={form.consequence_class} onValueChange={(v) => setForm({ ...form, consequence_class: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CC1">CC1 - Conséquences faibles</SelectItem>
                      <SelectItem value="CC2">CC2 - Conséquences moyennes</SelectItem>
                      <SelectItem value="CC3">CC3 - Conséquences élevées</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Zone sismique SIA 261</Label>
                  <Select value={form.seismic_zone} onValueChange={(v) => setForm({ ...form, seismic_zone: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {['Z1a', 'Z1b', 'Z2', 'Z3a', 'Z3b'].map((c) => (
                        <SelectItem key={c} value={c}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
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
            <Building className="h-10 w-10 mx-auto mb-2 text-muted-foreground" />
            Aucun modèle structure.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((m) => (
            <Link key={m.id} href={`/structure/${m.id}`}>
              <Card className="hover:border-primary transition-colors cursor-pointer h-full">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium truncate">{m.name}</h3>
                    <StatusBadge status="INFO" label={m.status} />
                  </div>
                  <p className="text-xs text-muted-foreground">{m.referentiel?.toUpperCase()} · {m.exposure_class}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {(m.nodes || []).length} nœuds · {(m.members || []).length} éléments
                  </p>
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

'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Building2, Plus, FileText, Calculator } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { VECTEURS_ENERGETIQUES } from '@/lib/ch';
import { formatDate } from '@/lib/utils';

export default function IDCPage() {
  const [buildings, setBuildings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<any>({
    ega: '',
    address: '',
    postal_code: '',
    sre_m2: 0,
    heating_energy_vector: 'gaz',
    building_year: null,
    nb_logements: null,
    regie_name: '',
  });
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const d = await api.idc.listBuildings();
      setBuildings(d.buildings);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.idc.createBuilding({
        ...form,
        sre_m2: Number(form.sre_m2),
        building_year: form.building_year ? Number(form.building_year) : null,
        nb_logements: form.nb_logements ? Number(form.nb_logements) : null,
      });
      setShowForm(false);
      setForm({ ...form, ega: '', address: '', sre_m2: 0 });
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
            <Building2 className="h-6 w-6" />
            IDC Genève
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Gestion annuelle de l'Indice de Dépense de Chaleur (LEn-GE / REn-GE)
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />
          Ajouter un bâtiment
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Nouveau bâtiment IDC</CardTitle>
            <CardDescription>
              Les informations EGID, SRE et vecteur énergétique sont nécessaires pour calculer l'IDC annuel.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>EGID (Identifiant fédéral du bâtiment)</Label>
                  <Input
                    placeholder="ex: 1234567"
                    value={form.ega}
                    onChange={(e) => setForm({ ...form, ega: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Adresse *</Label>
                  <Input
                    required
                    value={form.address}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Code postal</Label>
                  <Input
                    value={form.postal_code}
                    onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>SRE en m² *</Label>
                  <Input
                    type="number"
                    required
                    step="0.01"
                    value={form.sre_m2 || ''}
                    onChange={(e) => setForm({ ...form, sre_m2: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Vecteur de chauffage *</Label>
                  <Select
                    value={form.heating_energy_vector}
                    onValueChange={(v) => setForm({ ...form, heating_energy_vector: v })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {VECTEURS_ENERGETIQUES.map((v) => (
                        <SelectItem key={v.value} value={v.value}>
                          {v.label} ({v.unit})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Année de construction</Label>
                  <Input
                    type="number"
                    value={form.building_year || ''}
                    onChange={(e) => setForm({ ...form, building_year: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Nombre de logements</Label>
                  <Input
                    type="number"
                    value={form.nb_logements || ''}
                    onChange={(e) => setForm({ ...form, nb_logements: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Régie / gestionnaire</Label>
                  <Input
                    value={form.regie_name}
                    onChange={(e) => setForm({ ...form, regie_name: e.target.value })}
                  />
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

      <div className="rounded-md bg-blue-50 border border-blue-200 p-3 text-sm text-blue-900">
        <p><strong>ℹ À savoir sur l'IDC à Genève</strong></p>
        <p className="mt-1">
          À Genève, le CECB n'est pas systématiquement obligatoire. L'IDC (en MJ/m²/an) est l'instrument
          central de suivi énergétique annuel pour les bâtiments concernés par la LEn-GE. Vérifiez les
          seuils et obligations en vigueur sur le site OCEN avant toute soumission.
        </p>
      </div>

      {loading ? (
        <div className="text-muted-foreground">Chargement...</div>
      ) : buildings.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            <Building2 className="h-10 w-10 mx-auto mb-2 text-muted-foreground" />
            Aucun bâtiment enregistré. Ajoutez un bâtiment pour commencer le suivi IDC.
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {buildings.map((b) => (
            <Link key={b.id} href={`/idc/${b.id}`}>
              <Card className="hover:border-primary transition-colors cursor-pointer">
                <CardContent className="pt-6">
                  <p className="font-medium">{b.address}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    EGID {b.ega || '—'} · SRE {b.sre_m2} m² · {b.heating_energy_vector}
                  </p>
                  {b.nb_logements && (
                    <p className="text-xs text-muted-foreground">{b.nb_logements} logement(s)</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-2">Créé le {formatDate(b.created_at)}</p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

'use client';
import { useState } from 'react';
import { Plus, Save, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

// Listes de référence (libellé affiché ↔ valeur stockée)
const WALL_TYPES: Record<string, string> = {
  mur_exterieur: 'Mur extérieur',
  toiture: 'Toiture',
  dalle_sur_terrain: 'Dalle sur terrain',
  dalle_sur_local_non_chauffe: 'Dalle sur local non chauffé',
  mur_contre_terre: 'Mur contre terre',
  plancher: 'Plancher',
};
const OPENING_TYPES: Record<string, string> = {
  fenetre: 'Fenêtre',
  porte_vitree: 'Porte vitrée',
  porte_opaque: 'Porte opaque',
};
const ORIENTATIONS = ['N', 'S', 'E', 'O', 'horizontal'];
const NONE = '__none__';

type Row = Record<string, string>;

function uid() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

// Normalise une valeur du modèle (number|null) vers une chaîne éditable.
const s = (v: any): string => (v === null || v === undefined ? '' : String(v));

export function ThermalModelEditor({
  modelId,
  model,
  onSaved,
}: {
  modelId: string;
  model: any;
  onSaved: () => void;
}) {
  const [walls, setWalls] = useState<Row[]>(
    (model.walls || []).map((w: any) => ({
      id: w.id || uid(), type: w.type || 'mur_exterieur',
      orientation: w.orientation || NONE, area: s(w.area), u_value: s(w.u_value),
    })),
  );
  const [openings, setOpenings] = useState<Row[]>(
    (model.openings || []).map((o: any) => ({
      id: o.id || uid(), type: o.type || 'fenetre',
      orientation: o.orientation || NONE, area: s(o.area),
      u_value: s(o.u_value), g_value: s(o.g_value),
    })),
  );
  const [zones, setZones] = useState<Row[]>(
    (model.zones || []).map((z: any) => ({
      id: z.id || uid(), name: z.name || '', affectation: z.affectation || 'logement_collectif',
      area: s(z.area), volume: s(z.volume), temp_setpoint: s(z.temp_setpoint ?? 20),
    })),
  );
  const [bridges, setBridges] = useState<Row[]>(
    (model.thermal_bridges || []).map((b: any) => ({
      key: uid(), type: b.type || '', length: s(b.length), psi: s(b.psi),
    })),
  );

  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const touch = () => { setDirty(true); setSaved(false); };

  const num = (v: string): number | undefined => {
    if (v === '' || v === null || v === undefined) return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  };

  const handleSave = async () => {
    setError(null);
    // Validation client cohérente avec les garde-fous backend.
    const problems: string[] = [];
    walls.forEach((w, i) => {
      if (!(num(w.area)! > 0)) problems.push(`Paroi #${i + 1} : surface requise (> 0)`);
      const u = num(w.u_value);
      if (u !== undefined && !(u > 0 && u <= 10)) problems.push(`Paroi #${i + 1} : U hors plage ]0 ; 10]`);
    });
    openings.forEach((o, i) => {
      if (!(num(o.area)! > 0)) problems.push(`Ouverture #${i + 1} : surface requise (> 0)`);
      const u = num(o.u_value);
      if (u !== undefined && !(u > 0 && u <= 10)) problems.push(`Ouverture #${i + 1} : U hors plage ]0 ; 10]`);
      const g = num(o.g_value);
      if (g !== undefined && !(g >= 0 && g <= 1)) problems.push(`Ouverture #${i + 1} : facteur g hors [0 ; 1]`);
    });
    zones.forEach((z, i) => {
      if (!z.name.trim()) problems.push(`Zone #${i + 1} : nom requis`);
      if (!(num(z.area)! > 0)) problems.push(`Zone #${i + 1} : surface requise (> 0)`);
    });
    bridges.forEach((b, i) => {
      if (!b.type.trim()) problems.push(`Pont thermique #${i + 1} : type requis`);
      if (!(num(b.length)! > 0)) problems.push(`Pont thermique #${i + 1} : longueur requise (> 0)`);
      if (num(b.psi) === undefined) problems.push(`Pont thermique #${i + 1} : ψ requis`);
    });
    if (problems.length) { setError(problems.join(' · ')); return; }

    setSaving(true);
    try {
      await api.thermique.updateModel(modelId, {
        walls: walls.map((w) => ({
          id: w.id, type: w.type,
          orientation: w.orientation === NONE ? null : w.orientation,
          area: num(w.area), u_value: num(w.u_value),
        })),
        openings: openings.map((o) => ({
          id: o.id, type: o.type,
          orientation: o.orientation === NONE ? null : o.orientation,
          area: num(o.area), u_value: num(o.u_value), g_value: num(o.g_value),
        })),
        zones: zones.map((z) => ({
          id: z.id, name: z.name, affectation: z.affectation,
          area: num(z.area), volume: num(z.volume),
          temp_setpoint: num(z.temp_setpoint) ?? 20,
        })),
        thermal_bridges: bridges.map((b) => ({
          type: b.type, length: num(b.length), psi: num(b.psi),
        })),
      });
      setDirty(false);
      setSaved(true);
      onSaved();
    } catch (e: any) {
      setError(e.message || 'Échec de l’enregistrement');
    } finally {
      setSaving(false);
    }
  };

  const set = (
    rows: Row[], setter: (r: Row[]) => void, idx: number, field: string, value: string,
  ) => {
    const copy = rows.slice();
    copy[idx] = { ...copy[idx], [field]: value };
    setter(copy);
    touch();
  };
  const remove = (rows: Row[], setter: (r: Row[]) => void, idx: number) => {
    setter(rows.filter((_, i) => i !== idx));
    touch();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Composition du modèle</CardTitle>
        <CardDescription>
          Saisissez les parois, ouvertures, zones et ponts thermiques. Ces données pré-remplissent
          la fiche de saisie Lesosai et le calcul indicatif.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">

        {/* ---------------- PAROIS ---------------- */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold">Parois ({walls.length})</Label>
            <Button variant="outline" size="sm" onClick={() => {
              setWalls([...walls, { id: uid(), type: 'mur_exterieur', orientation: NONE, area: '10', u_value: '0.20' }]);
              touch();
            }}><Plus className="h-3 w-3 mr-1" /> Ajouter</Button>
          </div>
          {walls.length === 0 && <p className="text-xs text-muted-foreground">Aucune paroi.</p>}
          {walls.map((w, i) => (
            <div key={w.id} className="grid grid-cols-12 gap-2 items-center">
              <div className="col-span-4">
                <Select value={w.type} onValueChange={(v) => set(walls, setWalls, i, 'type', v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(WALL_TYPES).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-3">
                <Select value={w.orientation} onValueChange={(v) => set(walls, setWalls, i, 'orientation', v)}>
                  <SelectTrigger><SelectValue placeholder="Orient." /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>—</SelectItem>
                    {ORIENTATIONS.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <Input className="col-span-2" type="number" placeholder="m²" value={w.area}
                onChange={(e) => set(walls, setWalls, i, 'area', e.target.value)} />
              <Input className="col-span-2" type="number" step="0.01" placeholder="U" value={w.u_value}
                onChange={(e) => set(walls, setWalls, i, 'u_value', e.target.value)} />
              <Button variant="ghost" size="icon" className="col-span-1" onClick={() => remove(walls, setWalls, i)}>
                <Trash2 className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
          <p className="text-[11px] text-muted-foreground">Surface en m² · U en W/m²·K</p>
        </section>

        {/* ---------------- OUVERTURES ---------------- */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold">Ouvertures ({openings.length})</Label>
            <Button variant="outline" size="sm" onClick={() => {
              setOpenings([...openings, { id: uid(), type: 'fenetre', orientation: NONE, area: '2', u_value: '1.0', g_value: '0.5' }]);
              touch();
            }}><Plus className="h-3 w-3 mr-1" /> Ajouter</Button>
          </div>
          {openings.length === 0 && <p className="text-xs text-muted-foreground">Aucune ouverture.</p>}
          {openings.map((o, i) => (
            <div key={o.id} className="grid grid-cols-12 gap-2 items-center">
              <div className="col-span-3">
                <Select value={o.type} onValueChange={(v) => set(openings, setOpenings, i, 'type', v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(OPENING_TYPES).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-3">
                <Select value={o.orientation} onValueChange={(v) => set(openings, setOpenings, i, 'orientation', v)}>
                  <SelectTrigger><SelectValue placeholder="Orient." /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NONE}>—</SelectItem>
                    {ORIENTATIONS.map((or) => <SelectItem key={or} value={or}>{or}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <Input className="col-span-2" type="number" placeholder="m²" value={o.area}
                onChange={(e) => set(openings, setOpenings, i, 'area', e.target.value)} />
              <Input className="col-span-2" type="number" step="0.01" placeholder="U" value={o.u_value}
                onChange={(e) => set(openings, setOpenings, i, 'u_value', e.target.value)} />
              <Input className="col-span-1" type="number" step="0.01" placeholder="g" value={o.g_value}
                onChange={(e) => set(openings, setOpenings, i, 'g_value', e.target.value)} />
              <Button variant="ghost" size="icon" className="col-span-1" onClick={() => remove(openings, setOpenings, i)}>
                <Trash2 className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
          <p className="text-[11px] text-muted-foreground">U en W/m²·K · g = facteur solaire [0 ; 1]</p>
        </section>

        {/* ---------------- ZONES ---------------- */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold">Zones ({zones.length})</Label>
            <Button variant="outline" size="sm" onClick={() => {
              setZones([...zones, { id: uid(), name: `Zone ${zones.length + 1}`, affectation: 'logement_collectif', area: '100', volume: '290', temp_setpoint: '20' }]);
              touch();
            }}><Plus className="h-3 w-3 mr-1" /> Ajouter</Button>
          </div>
          {zones.length === 0 && <p className="text-xs text-muted-foreground">Aucune zone.</p>}
          {zones.map((z, i) => (
            <div key={z.id} className="grid grid-cols-12 gap-2 items-center">
              <Input className="col-span-4" placeholder="Nom" value={z.name}
                onChange={(e) => set(zones, setZones, i, 'name', e.target.value)} />
              <Input className="col-span-3" placeholder="Affectation" value={z.affectation}
                onChange={(e) => set(zones, setZones, i, 'affectation', e.target.value)} />
              <Input className="col-span-2" type="number" placeholder="m²" value={z.area}
                onChange={(e) => set(zones, setZones, i, 'area', e.target.value)} />
              <Input className="col-span-2" type="number" placeholder="m³" value={z.volume}
                onChange={(e) => set(zones, setZones, i, 'volume', e.target.value)} />
              <Button variant="ghost" size="icon" className="col-span-1" onClick={() => remove(zones, setZones, i)}>
                <Trash2 className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
          <p className="text-[11px] text-muted-foreground">Surface (m²) et volume (m³) chauffés par zone</p>
        </section>

        {/* ---------------- PONTS THERMIQUES ---------------- */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold">Ponts thermiques ({bridges.length})</Label>
            <Button variant="outline" size="sm" onClick={() => {
              setBridges([...bridges, { key: uid(), type: 'Liaison balcon', length: '5', psi: '0.30' }]);
              touch();
            }}><Plus className="h-3 w-3 mr-1" /> Ajouter</Button>
          </div>
          {bridges.length === 0 && <p className="text-xs text-muted-foreground">Aucun pont thermique.</p>}
          {bridges.map((b, i) => (
            <div key={b.key} className="grid grid-cols-12 gap-2 items-center">
              <Input className="col-span-6" placeholder="Type (ex. liaison balcon)" value={b.type}
                onChange={(e) => set(bridges, setBridges, i, 'type', e.target.value)} />
              <Input className="col-span-2" type="number" placeholder="ml" value={b.length}
                onChange={(e) => set(bridges, setBridges, i, 'length', e.target.value)} />
              <Input className="col-span-3" type="number" step="0.01" placeholder="ψ" value={b.psi}
                onChange={(e) => set(bridges, setBridges, i, 'psi', e.target.value)} />
              <Button variant="ghost" size="icon" className="col-span-1" onClick={() => remove(bridges, setBridges, i)}>
                <Trash2 className="h-4 w-4 text-muted-foreground" />
              </Button>
            </div>
          ))}
          <p className="text-[11px] text-muted-foreground">Longueur en mètres linéaires · ψ en W/m·K</p>
        </section>

        {error && <div className="text-sm text-destructive">{error}</div>}

        <div className="flex items-center gap-3 pt-2 border-t">
          <Button onClick={handleSave} disabled={saving || !dirty}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Enregistrement…' : 'Enregistrer la composition'}
          </Button>
          {saved && !dirty && <span className="text-sm text-emerald-700">Enregistré ✓</span>}
          {dirty && !saving && <span className="text-sm text-amber-700">Modifications non enregistrées</span>}
        </div>
      </CardContent>
    </Card>
  );
}

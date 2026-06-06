'use client';
import { useState } from 'react';
import { BookmarkPlus, Library, Plus, Save, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { GENERATEURS_CHALEUR, VECTEURS_ENERGETIQUES, VENTILATION_TYPES } from '@/lib/ch';

// Listes de référence (libellé affiché ↔ valeur stockée)
const WALL_TYPES: Record<string, string> = {
  mur_exterieur: 'Mur extérieur',
  toiture: 'Toiture',
  dalle_sur_terrain: 'Dalle sur terrain',
  dalle_sur_exterieur: 'Dalle sur extérieur',
  dalle_sur_local_non_chauffe: 'Dalle sur local non chauffé',
  mur_contre_terre: 'Mur contre terre',
  mur_local_non_chauffe: 'Mur contre local non chauffé',
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

// ----------------------------------------------------------------------------
// Catalogue de compositions réutilisables — mémorisé sur le navigateur.
// Permet à l'ingénieur de retrouver ses parois/ouvertures d'un projet à l'autre.
// ----------------------------------------------------------------------------
const CATALOG_KEY = 'leso_thermal_catalog_v1';
type CatalogItem = { name: string; type: string; u_value: string; g_value?: string };
type Catalog = { walls: CatalogItem[]; openings: CatalogItem[] };

function loadCatalog(): Catalog {
  if (typeof window === 'undefined') return { walls: [], openings: [] };
  try {
    const raw = window.localStorage.getItem(CATALOG_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return { walls: parsed?.walls || [], openings: parsed?.openings || [] };
  } catch {
    return { walls: [], openings: [] };
  }
}

function saveCatalog(c: Catalog) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(CATALOG_KEY, JSON.stringify(c));
  } catch {
    /* quota / mode privé : on ignore silencieusement */
  }
}

export function ThermalModelEditor({
  modelId,
  model,
  onSaved,
  onDirtyChange,
}: {
  modelId: string;
  model: any;
  onSaved: () => void;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const [walls, setWalls] = useState<Row[]>(
    (model.walls || []).map((w: any) => ({
      id: w.id || uid(), name: w.name || '', type: w.type || 'mur_exterieur',
      orientation: w.orientation || NONE, area: s(w.area), u_value: s(w.u_value),
    })),
  );
  const [openings, setOpenings] = useState<Row[]>(
    (model.openings || []).map((o: any) => ({
      id: o.id || uid(), name: o.name || '', type: o.type || 'fenetre',
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

  // SRE explicite (override). Vide = calculée automatiquement depuis les zones.
  const [sre, setSre] = useState<string>(s(model.hypotheses?.sre_m2));

  // Installations techniques
  const sys = model.systems || {};
  const [heating, setHeating] = useState<Row>({
    vector: sys.heating?.vector || NONE,
    generator: sys.heating?.generator || NONE,
    efficiency: s(sys.heating?.efficiency),
  });
  const [ventilation, setVentilation] = useState<Row>({
    type: sys.ventilation?.type || NONE,
    heat_recovery_pct: s(sys.ventilation?.heat_recovery_pct),
  });
  const [ecs, setEcs] = useState<Row>({
    vector: sys.ecs?.vector || NONE,
    storage_liters: s(sys.ecs?.storage_liters),
  });

  const [catalog, setCatalog] = useState<Catalog>(loadCatalog);
  const [showWallCat, setShowWallCat] = useState(false);
  const [showOpeningCat, setShowOpeningCat] = useState(false);

  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const touch = () => { setDirty(true); setSaved(false); onDirtyChange?.(true); };

  const num = (v: string): number | undefined => {
    if (v === '' || v === null || v === undefined) return undefined;
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  };

  const sreComputed = zones.reduce((sum, z) => sum + (num(z.area) || 0), 0);

  // ---- catalogue ----
  const addWallToCatalog = (w: Row) => {
    const name = (w.name || '').trim();
    if (!name) { setError('Donnez une désignation à la paroi avant de l’ajouter au catalogue.'); return; }
    const item: CatalogItem = { name, type: w.type, u_value: w.u_value };
    const next = { ...catalog, walls: [item, ...catalog.walls.filter((x) => x.name !== name)].slice(0, 50) };
    setCatalog(next); saveCatalog(next); setError(null);
  };
  const addOpeningToCatalog = (o: Row) => {
    const name = (o.name || '').trim();
    if (!name) { setError('Donnez une désignation à l’ouverture avant de l’ajouter au catalogue.'); return; }
    const item: CatalogItem = { name, type: o.type, u_value: o.u_value, g_value: o.g_value };
    const next = { ...catalog, openings: [item, ...catalog.openings.filter((x) => x.name !== name)].slice(0, 50) };
    setCatalog(next); saveCatalog(next); setError(null);
  };
  const useWallFromCatalog = (item: CatalogItem) => {
    setWalls([...walls, { id: uid(), name: item.name, type: item.type, orientation: NONE, area: '10', u_value: item.u_value || '0.20' }]);
    setShowWallCat(false); touch();
  };
  const useOpeningFromCatalog = (item: CatalogItem) => {
    setOpenings([...openings, { id: uid(), name: item.name, type: item.type, orientation: NONE, area: '2', u_value: item.u_value || '1.0', g_value: item.g_value || '0.5' }]);
    setShowOpeningCat(false); touch();
  };
  const removeWallFromCatalog = (name: string) => {
    const next = { ...catalog, walls: catalog.walls.filter((x) => x.name !== name) };
    setCatalog(next); saveCatalog(next);
  };
  const removeOpeningFromCatalog = (name: string) => {
    const next = { ...catalog, openings: catalog.openings.filter((x) => x.name !== name) };
    setCatalog(next); saveCatalog(next);
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
    const sreVal = num(sre);
    if (sreVal !== undefined && !(sreVal > 0)) problems.push('SRE : valeur invalide (> 0 ou laisser vide)');
    const hr = num(ventilation.heat_recovery_pct);
    if (hr !== undefined && !(hr >= 0 && hr <= 100)) problems.push('Ventilation : récupération de chaleur hors [0 ; 100] %');
    if (problems.length) { setError(problems.join(' · ')); return; }

    // Installations techniques : on repart des systèmes existants (pour préserver
    // d'éventuels sous-blocs non gérés ici, ex. refroidissement) et on met à jour
    // chauffage / ventilation / ECS — supprimés s'ils sont vidés.
    const systems: any = { ...(model.systems || {}) };
    if (heating.vector !== NONE || heating.generator !== NONE || heating.efficiency) {
      systems.heating = {
        vector: heating.vector === NONE ? null : heating.vector,
        generator: heating.generator === NONE ? null : heating.generator,
        efficiency: num(heating.efficiency) ?? null,
      };
    } else {
      delete systems.heating;
    }
    if (ventilation.type !== NONE || ventilation.heat_recovery_pct) {
      systems.ventilation = {
        type: ventilation.type === NONE ? null : ventilation.type,
        heat_recovery_pct: num(ventilation.heat_recovery_pct) ?? null,
      };
    } else {
      delete systems.ventilation;
    }
    if (ecs.vector !== NONE || ecs.storage_liters) {
      systems.ecs = {
        vector: ecs.vector === NONE ? null : ecs.vector,
        storage_liters: num(ecs.storage_liters) ?? null,
      };
    } else {
      delete systems.ecs;
    }

    setSaving(true);
    try {
      await api.thermique.updateModel(modelId, {
        walls: walls.map((w) => ({
          id: w.id, name: w.name || null, type: w.type,
          orientation: w.orientation === NONE ? null : w.orientation,
          area: num(w.area), u_value: num(w.u_value),
        })),
        openings: openings.map((o) => ({
          id: o.id, name: o.name || null, type: o.type,
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
        systems,
        hypotheses: { ...(model.hypotheses || {}), sre_m2: sreVal ?? null },
      });
      setDirty(false);
      setSaved(true);
      onDirtyChange?.(false);
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
  const setSys = (setter: (r: Row) => void, current: Row, field: string, value: string) => {
    setter({ ...current, [field]: value });
    touch();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Composition du modèle</CardTitle>
        <CardDescription>
          Saisissez la SRE, les parois, ouvertures, zones, installations techniques et ponts
          thermiques. Ces données alimentent la fiche de saisie Lesosai et le calcul indicatif.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">

        {/* ---------------- SRE ---------------- */}
        <section className="space-y-2">
          <Label className="text-sm font-semibold">Surface de référence énergétique (SRE)</Label>
          <div className="flex items-center gap-3">
            <Input
              type="number" className="w-40" placeholder={sreComputed > 0 ? String(sreComputed) : 'm²'}
              value={sre}
              onChange={(e) => { setSre(e.target.value); touch(); }}
            />
            <span className="text-xs text-muted-foreground">
              m² · Laisser vide pour utiliser la somme des zones
              {sreComputed > 0 && <> (≈ <strong>{sreComputed.toLocaleString('fr-CH')} m²</strong>)</>}
            </span>
          </div>
        </section>

        {/* ---------------- PAROIS ---------------- */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold">Parois opaques ({walls.length})</Label>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowWallCat((v) => !v)}>
                <Library className="h-3 w-3 mr-1" /> Catalogue ({catalog.walls.length})
              </Button>
              <Button variant="outline" size="sm" onClick={() => {
                setWalls([...walls, { id: uid(), name: '', type: 'mur_exterieur', orientation: NONE, area: '10', u_value: '0.20' }]);
                touch();
              }}><Plus className="h-3 w-3 mr-1" /> Ajouter</Button>
            </div>
          </div>

          {showWallCat && (
            <div className="rounded-md border bg-muted/40 p-2 space-y-1">
              {catalog.walls.length === 0 && <p className="text-xs text-muted-foreground">Catalogue vide. Cliquez sur l’icône signet d’une paroi pour la mémoriser.</p>}
              {catalog.walls.map((c) => (
                <div key={c.name} className="flex items-center justify-between gap-2 text-xs">
                  <button className="flex-1 text-left hover:underline" onClick={() => useWallFromCatalog(c)}>
                    <span className="font-medium">{c.name}</span>
                    <span className="text-muted-foreground"> · {WALL_TYPES[c.type] || c.type} · U={c.u_value || '?'}</span>
                  </button>
                  <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeWallFromCatalog(c.name)}>
                    <Trash2 className="h-3 w-3 text-muted-foreground" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {walls.length === 0 && <p className="text-xs text-muted-foreground">Aucune paroi.</p>}
          {walls.map((w, i) => (
            <div key={w.id} className="rounded-md border p-2 space-y-2">
              <div className="flex items-center gap-2">
                <Input
                  className="flex-1" placeholder="Désignation (ex. Mur ext. type A — béton + 18 cm laine)"
                  value={w.name}
                  onChange={(e) => set(walls, setWalls, i, 'name', e.target.value)}
                />
                <Button variant="ghost" size="icon" title="Mémoriser au catalogue" onClick={() => addWallToCatalog(w)}>
                  <BookmarkPlus className="h-4 w-4 text-muted-foreground" />
                </Button>
                <Button variant="ghost" size="icon" title="Supprimer" onClick={() => remove(walls, setWalls, i)}>
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </div>
              <div className="grid grid-cols-12 gap-2 items-center">
                <div className="col-span-5">
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
              </div>
            </div>
          ))}
          <p className="text-[11px] text-muted-foreground">Surface en m² · U en W/m²·K</p>
        </section>

        {/* ---------------- OUVERTURES ---------------- */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-semibold">Ouvertures ({openings.length})</Label>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowOpeningCat((v) => !v)}>
                <Library className="h-3 w-3 mr-1" /> Catalogue ({catalog.openings.length})
              </Button>
              <Button variant="outline" size="sm" onClick={() => {
                setOpenings([...openings, { id: uid(), name: '', type: 'fenetre', orientation: NONE, area: '2', u_value: '1.0', g_value: '0.5' }]);
                touch();
              }}><Plus className="h-3 w-3 mr-1" /> Ajouter</Button>
            </div>
          </div>

          {showOpeningCat && (
            <div className="rounded-md border bg-muted/40 p-2 space-y-1">
              {catalog.openings.length === 0 && <p className="text-xs text-muted-foreground">Catalogue vide. Cliquez sur l’icône signet d’une ouverture pour la mémoriser.</p>}
              {catalog.openings.map((c) => (
                <div key={c.name} className="flex items-center justify-between gap-2 text-xs">
                  <button className="flex-1 text-left hover:underline" onClick={() => useOpeningFromCatalog(c)}>
                    <span className="font-medium">{c.name}</span>
                    <span className="text-muted-foreground"> · {OPENING_TYPES[c.type] || c.type} · U={c.u_value || '?'} · g={c.g_value || '?'}</span>
                  </button>
                  <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => removeOpeningFromCatalog(c.name)}>
                    <Trash2 className="h-3 w-3 text-muted-foreground" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {openings.length === 0 && <p className="text-xs text-muted-foreground">Aucune ouverture.</p>}
          {openings.map((o, i) => (
            <div key={o.id} className="rounded-md border p-2 space-y-2">
              <div className="flex items-center gap-2">
                <Input
                  className="flex-1" placeholder="Désignation (ex. Fenêtre triple vitrage bois-métal)"
                  value={o.name}
                  onChange={(e) => set(openings, setOpenings, i, 'name', e.target.value)}
                />
                <Button variant="ghost" size="icon" title="Mémoriser au catalogue" onClick={() => addOpeningToCatalog(o)}>
                  <BookmarkPlus className="h-4 w-4 text-muted-foreground" />
                </Button>
                <Button variant="ghost" size="icon" title="Supprimer" onClick={() => remove(openings, setOpenings, i)}>
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </div>
              <div className="grid grid-cols-12 gap-2 items-center">
                <div className="col-span-4">
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
              </div>
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
          {zones.length > 0 && (
            <div className="grid grid-cols-12 gap-2 text-[11px] font-medium text-muted-foreground px-1">
              <span className="col-span-4">Nom de la zone</span>
              <span className="col-span-3">Affectation</span>
              <span className="col-span-2">Surface (m²)</span>
              <span className="col-span-2">Volume (m³)</span>
              <span className="col-span-1" />
            </div>
          )}
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

        {/* ---------------- INSTALLATIONS TECHNIQUES ---------------- */}
        <section className="space-y-3">
          <Label className="text-sm font-semibold">Installations techniques</Label>

          <div className="grid md:grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Chauffage — vecteur</Label>
              <Select value={heating.vector} onValueChange={(v) => setSys(setHeating, heating, 'vector', v)}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {VECTEURS_ENERGETIQUES.map((v) => <SelectItem key={v.value} value={v.value}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Générateur de chaleur</Label>
              <Select value={heating.generator} onValueChange={(v) => setSys(setHeating, heating, 'generator', v)}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {GENERATEURS_CHALEUR.map((g) => <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Rendement / COP (optionnel)</Label>
              <Input type="number" step="0.01" placeholder="ex. 3.5 (COP) ou 0.92"
                value={heating.efficiency}
                onChange={(e) => setSys(setHeating, heating, 'efficiency', e.target.value)} />
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Ventilation — type</Label>
              <Select value={ventilation.type} onValueChange={(v) => setSys(setVentilation, ventilation, 'type', v)}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {VENTILATION_TYPES.map((v) => <SelectItem key={v.value} value={v.value}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Récupération de chaleur (%)</Label>
              <Input type="number" placeholder="ex. 80" value={ventilation.heat_recovery_pct}
                onChange={(e) => setSys(setVentilation, ventilation, 'heat_recovery_pct', e.target.value)} />
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">ECS — vecteur</Label>
              <Select value={ecs.vector} onValueChange={(v) => setSys(setEcs, ecs, 'vector', v)}>
                <SelectTrigger><SelectValue placeholder="—" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>—</SelectItem>
                  {VECTEURS_ENERGETIQUES.map((v) => <SelectItem key={v.value} value={v.value}>{v.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Stockage ECS (litres)</Label>
              <Input type="number" placeholder="ex. 500" value={ecs.storage_liters}
                onChange={(e) => setSys(setEcs, ecs, 'storage_liters', e.target.value)} />
            </div>
          </div>
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
          {bridges.length > 0 && (
            <div className="grid grid-cols-12 gap-2 text-[11px] font-medium text-muted-foreground px-1">
              <span className="col-span-6">Type de liaison</span>
              <span className="col-span-2">Longueur (ml)</span>
              <span className="col-span-3">ψ (W/m·K)</span>
              <span className="col-span-1" />
            </div>
          )}
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

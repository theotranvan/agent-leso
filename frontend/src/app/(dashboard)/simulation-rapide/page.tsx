'use client';
import { useState } from 'react';
import {
  Zap, Loader2, Download, AlertCircle, CheckCircle2, Calculator,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const CANTONS = ['GE', 'VD', 'NE', 'FR', 'VS', 'JU', 'BE', 'BS', 'ZH'];
const AFFECTATIONS = [
  { v: 'logement_collectif', l: 'Logement collectif' },
  { v: 'logement_individuel', l: 'Logement individuel' },
  { v: 'administration', l: 'Administration / bureaux' },
  { v: 'ecole', l: 'École' },
  { v: 'commerce', l: 'Commerce' },
  { v: 'hopital', l: 'Hôpital' },
  { v: 'industriel', l: 'Industriel' },
];
const STANDARDS = [
  { v: 'sia_380_1_neuf', l: 'SIA 380/1 neuf' },
  { v: 'minergie', l: 'MINERGIE' },
  { v: 'minergie_p', l: 'MINERGIE-P' },
  { v: 'renovation_qualifiee', l: 'Rénovation qualifiée' },
  { v: 'existant_1980', l: 'Existant (avant 1980)' },
];
const VECTEURS = [
  'gaz', 'mazout', 'chauffage_distance', 'pac_air_eau', 'pac_sol_eau',
  'pellet', 'buche', 'electrique',
];
const FORMES = [
  { v: 'compact', l: 'Compact (immeuble collectif)' },
  { v: 'standard', l: 'Standard (petit collectif)' },
  { v: 'etale', l: 'Étalé (villa avec décrochés)' },
  { v: 'tres_etale', l: 'Très étalé (plain-pied)' },
];

export default function SimulationRapidePage() {
  const [form, setForm] = useState({
    sre_m2: 1000,
    affectation: 'logement_collectif',
    canton: 'GE',
    standard: 'sia_380_1_neuf',
    operation_type: 'neuf',
    heating_vector: 'gaz',
    facteur_forme: 'standard',
    fraction_ouvertures: 0.25,
    project_name: '',
    author: '',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const handleCompute = async () => {
    setError(null);
    setLoading(true);
    try {
      const r = await api.v4.simulationRapide.create(form);
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Zap className="h-6 w-6 text-amber-600" />
        <div>
          <h1 className="text-2xl font-semibold">Simulation énergétique rapide</h1>
          <p className="text-sm text-muted-foreground">
            Pré-étude SIA 380/1 en 30 secondes — sans IFC, depuis le programme
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Paramètres du bâtiment</CardTitle>
          <CardDescription>
            Calcul forfaitaire à vocation avant-projet. Ne remplace pas un calcul Lesosai officiel.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Nom du projet</Label>
              <Input
                value={form.project_name}
                onChange={(e) => set('project_name', e.target.value)}
                placeholder="Ex : Villa Dupont"
              />
            </div>
            <div>
              <Label>Thermicien signataire</Label>
              <Input
                value={form.author}
                onChange={(e) => set('author', e.target.value)}
                placeholder="Prénom Nom"
              />
            </div>
            <div>
              <Label>SRE (m²)</Label>
              <Input
                type="number"
                min={1}
                value={form.sre_m2}
                onChange={(e) => set('sre_m2', Number(e.target.value))}
              />
            </div>
            <div>
              <Label>Canton</Label>
              <Select value={form.canton} onValueChange={(v) => set('canton', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CANTONS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Affectation</Label>
              <Select value={form.affectation} onValueChange={(v) => set('affectation', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {AFFECTATIONS.map((a) => <SelectItem key={a.v} value={a.v}>{a.l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Standard visé</Label>
              <Select value={form.standard} onValueChange={(v) => set('standard', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STANDARDS.map((s) => <SelectItem key={s.v} value={s.v}>{s.l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Vecteur de chauffage</Label>
              <Select value={form.heating_vector} onValueChange={(v) => set('heating_vector', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {VECTEURS.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Forme du bâtiment</Label>
              <Select value={form.facteur_forme} onValueChange={(v) => set('facteur_forme', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FORMES.map((f) => <SelectItem key={f.v} value={f.v}>{f.l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Fraction d'ouvertures (0-1)</Label>
              <Input
                type="number" step={0.05} min={0} max={0.8}
                value={form.fraction_ouvertures}
                onChange={(e) => set('fraction_ouvertures', Number(e.target.value))}
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-600 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" /> {error}
            </div>
          )}

          <Button onClick={handleCompute} disabled={loading} className="w-full">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Calculator className="h-4 w-4 mr-2" />}
            Calculer
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Résultat</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Qh</p>
                <p className="text-xl font-semibold">{result.main_variant?.qh_kwh_m2_an}</p>
                <p className="text-xs text-muted-foreground">kWh/m²·an</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Ep</p>
                <p className="text-xl font-semibold">{result.main_variant?.ep_kwh_m2_an}</p>
                <p className="text-xs text-muted-foreground">kWh/m²·an</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Classe</p>
                <p className="text-xl font-semibold">{result.main_variant?.energy_class}</p>
                <p className="text-xs text-muted-foreground">A → G</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Conformité</p>
                <p className="text-xl font-semibold flex items-center gap-1">
                  {result.main_variant?.compliant ? (
                    <><CheckCircle2 className="h-5 w-5 text-emerald-600" /> OK</>
                  ) : (
                    <><AlertCircle className="h-5 w-5 text-amber-600" /> NON</>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">estimatif</p>
              </div>
            </div>

            {result.result_url && (
              <Button asChild variant="outline">
                <a href={result.result_url} target="_blank" rel="noopener noreferrer" download>
                  <Download className="h-3.5 w-3.5 mr-2" />
                  Télécharger le rapport PDF
                </a>
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

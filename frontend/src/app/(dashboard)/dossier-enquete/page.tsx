'use client';
import { useState } from 'react';
import { FileText, Loader2, AlertCircle, CheckCircle2, Download } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const AFFECTATIONS = [
  'logement_collectif', 'logement_individuel', 'administration',
  'commerce', 'industriel', 'mixte',
];

export default function DossierEnquetePage() {
  const [form, setForm] = useState({
    project_name: '',
    canton: 'GE',
    address: '',
    affectation: 'logement_collectif',
    operation_type: 'neuf',
    sre_m2: 0,
    volume_sia: 0,
    terrain_m2: 0,
    zone: '',
    nb_logements: 0,
    specificities: '',
    author: '',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (k: string, v: any) => setForm((f) => ({ ...f, [k]: v }));

  const handleGenerate = async () => {
    setError(null);
    setLoading(true);
    try {
      const body = {
        project_name: form.project_name,
        project_data: {
          canton: form.canton,
          address: form.address,
          affectation: form.affectation,
          operation_type: form.operation_type,
          sre_m2: form.sre_m2,
          volume_sia: form.volume_sia,
          terrain_m2: form.terrain_m2,
          zone: form.zone,
          nb_logements: form.nb_logements,
        },
        specificities: form.specificities,
        author: form.author,
      };
      const r = await api.v4.dossierEnquete.create(body);
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
        <FileText className="h-6 w-6 text-blue-600" />
        <div>
          <h1 className="text-2xl font-semibold">Dossier de mise en enquête</h1>
          <p className="text-sm text-muted-foreground">
            Mémoire justificatif APA (Genève) ou APC (Vaud) — économise 5 à 10 jours par affaire
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Informations du projet</CardTitle>
          <CardDescription>
            L'agent matchera automatiquement vos documents uploadés avec la liste des pièces attendues.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Nom du projet</Label>
              <Input value={form.project_name} onChange={(e) => set('project_name', e.target.value)} />
            </div>
            <div>
              <Label>Canton</Label>
              <Select value={form.canton} onValueChange={(v) => set('canton', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="GE">GE — APA</SelectItem>
                  <SelectItem value="VD">VD — APC</SelectItem>
                  <SelectItem value="NE">NE</SelectItem>
                  <SelectItem value="FR">FR</SelectItem>
                  <SelectItem value="VS">VS</SelectItem>
                  <SelectItem value="JU">JU</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="col-span-2">
              <Label>Adresse du projet</Label>
              <Input value={form.address} onChange={(e) => set('address', e.target.value)} />
            </div>
            <div>
              <Label>Affectation</Label>
              <Select value={form.affectation} onValueChange={(v) => set('affectation', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {AFFECTATIONS.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Opération</Label>
              <Select value={form.operation_type} onValueChange={(v) => set('operation_type', v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="neuf">Construction neuve</SelectItem>
                  <SelectItem value="renovation">Rénovation</SelectItem>
                  <SelectItem value="transformation">Transformation</SelectItem>
                  <SelectItem value="surelevation">Surélévation</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>SRE (m²)</Label>
              <Input type="number" value={form.sre_m2}
                onChange={(e) => set('sre_m2', Number(e.target.value))} />
            </div>
            <div>
              <Label>Volume SIA 416 (m³)</Label>
              <Input type="number" value={form.volume_sia}
                onChange={(e) => set('volume_sia', Number(e.target.value))} />
            </div>
            <div>
              <Label>Terrain (m²)</Label>
              <Input type="number" value={form.terrain_m2}
                onChange={(e) => set('terrain_m2', Number(e.target.value))} />
            </div>
            <div>
              <Label>Zone d'affectation</Label>
              <Input value={form.zone} onChange={(e) => set('zone', e.target.value)}
                placeholder="Ex : Zone 3 de développement" />
            </div>
            <div>
              <Label>Nb logements</Label>
              <Input type="number" value={form.nb_logements}
                onChange={(e) => set('nb_logements', Number(e.target.value))} />
            </div>
            <div>
              <Label>Architecte / BET signataire</Label>
              <Input value={form.author} onChange={(e) => set('author', e.target.value)} />
            </div>
          </div>

          <div>
            <Label>Spécificités du projet</Label>
            <Textarea
              value={form.specificities}
              onChange={(e) => set('specificities', e.target.value)}
              placeholder="Dérogation de gabarit, abattage d'arbres protégés, parking souterrain sur nappe, etc."
              className="min-h-[80px]"
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" /> {error}
            </div>
          )}

          <Button onClick={handleGenerate} disabled={loading || !form.project_name} className="w-full">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <FileText className="h-4 w-4 mr-2" />}
            Générer le mémoire justificatif
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              Dossier préparé
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Pièces attendues</p>
                <p className="text-xl font-semibold">{result.nb_pieces_attendues}</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Pièces manquantes</p>
                <p className="text-xl font-semibold text-amber-600">{result.nb_pieces_manquantes}</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Couverture</p>
                <p className="text-xl font-semibold">{result.coverage_pct}%</p>
              </div>
            </div>

            {result.result_url && (
              <Button asChild variant="outline">
                <a href={result.result_url} target="_blank" rel="noopener noreferrer" download>
                  <Download className="h-3.5 w-3.5 mr-2" />
                  Télécharger le mémoire PDF
                </a>
              </Button>
            )}

            <p className="text-xs text-muted-foreground">
              Le dossier préparatoire inclut : mémoire justificatif technique (10 sections),
              tableau SIA 416 des surfaces, et checklist de dépôt consolidée.
              L'architecte + l'ingénieur signent avant dépôt officiel.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

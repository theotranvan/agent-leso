'use client';
import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Download, Upload, Zap, ShieldCheck, Grid3x3 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge } from '@/components/swiss/StatusBadge';

export default function StructureDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [model, setModel] = useState<any>(null);
  const [safResult, setSafResult] = useState<any>(null);
  const [resultsFile, setResultsFile] = useState<File | null>(null);
  const [engineerValidated, setEngineerValidated] = useState(false);
  const [authorName, setAuthorName] = useState('');
  const [importResult, setImportResult] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Saisie paramétrique de la trame (géométrie d'avant-projet)
  const [geo, setGeo] = useState({
    n_levels: '3', n_bays_x: '3', bay_x_m: '5.4', n_bays_y: '2', bay_y_m: '6.0',
    story_height_m: '2.8', column_section: 'POT_30x30', beam_section: 'POU_30x50', material: 'C30/37',
  });
  const [geoBuilding, setGeoBuilding] = useState(false);
  const [geoSummary, setGeoSummary] = useState<any>(null);

  const handleGenerateGeometry = async () => {
    setError(null);
    setGeoBuilding(true);
    try {
      const r = await api.structure.generateGeometry(id, {
        n_levels: Number(geo.n_levels),
        n_bays_x: Number(geo.n_bays_x),
        bay_x_m: Number(geo.bay_x_m),
        n_bays_y: Number(geo.n_bays_y),
        bay_y_m: Number(geo.bay_y_m),
        story_height_m: Number(geo.story_height_m),
        column_section: geo.column_section,
        beam_section: geo.beam_section,
        material: geo.material,
      });
      setGeoSummary(r.summary);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGeoBuilding(false);
    }
  };

  const load = async () => {
    try {
      const m = await api.structure.getModel(id);
      setModel(m);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleGenerateSaf = async () => {
    setError(null);
    setGenerating(true);
    try {
      const r = await api.structure.generateSaf(id);
      setSafResult(r);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleImport = async () => {
    if (!resultsFile) return;
    if (!engineerValidated) {
      setError('Vous devez valider en tant qu\'ingénieur avant import des résultats.');
      return;
    }
    setError(null);
    setImporting(true);
    try {
      const r = await api.structure.importResults(id, resultsFile, engineerValidated, authorName);
      setImportResult(r);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setImporting(false);
    }
  };

  if (!model) return <div className="text-muted-foreground">Chargement...</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/structure" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Retour
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{model.name}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {model.referentiel?.toUpperCase()} · Exposition {model.exposure_class} · Séisme {model.seismic_zone}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Grid3x3 className="h-4 w-4" /> Étape 0 — Saisir la trame (géométrie d'avant-projet)
          </CardTitle>
          <CardDescription>
            Décrivez la trame régulière du bâtiment : LESO génère nœuds, poteaux, poutres et appuis.
            Optionnel — vous pouvez aussi partir d'un IFC (pré-BIM) ou bâtir la géométrie directement
            dans votre logiciel. Le calcul de résistance reste fait dans Scia/RFEM.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="space-y-1">
              <Label className="text-xs">Niveaux (étages)</Label>
              <Input type="number" min="1" value={geo.n_levels}
                onChange={(e) => setGeo({ ...geo, n_levels: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hauteur d'étage (m)</Label>
              <Input type="number" step="0.1" value={geo.story_height_m}
                onChange={(e) => setGeo({ ...geo, story_height_m: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Matériau</Label>
              <Select value={geo.material} onValueChange={(v) => setGeo({ ...geo, material: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['C25/30', 'C30/37', 'C35/45', 'S235', 'S355', 'GL24h'].map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Travées X (nb)</Label>
              <Input type="number" min="1" value={geo.n_bays_x}
                onChange={(e) => setGeo({ ...geo, n_bays_x: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Entraxe X (m)</Label>
              <Input type="number" step="0.1" value={geo.bay_x_m}
                onChange={(e) => setGeo({ ...geo, bay_x_m: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Section poteau</Label>
              <Select value={geo.column_section} onValueChange={(v) => setGeo({ ...geo, column_section: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['POT_25x25', 'POT_30x30', 'HEB200'].map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Travées Y (nb)</Label>
              <Input type="number" min="1" value={geo.n_bays_y}
                onChange={(e) => setGeo({ ...geo, n_bays_y: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Entraxe Y (m)</Label>
              <Input type="number" step="0.1" value={geo.bay_y_m}
                onChange={(e) => setGeo({ ...geo, bay_y_m: e.target.value })} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Section poutre</Label>
              <Select value={geo.beam_section} onValueChange={(v) => setGeo({ ...geo, beam_section: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {['POU_30x50', 'IPE200', 'HEB200'].map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button onClick={handleGenerateGeometry} disabled={geoBuilding} variant="outline">
            <Grid3x3 className="h-4 w-4 mr-2" />
            {geoBuilding ? 'Génération de la trame...' : 'Générer la géométrie'}
          </Button>
          {geoSummary && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs grid grid-cols-2 md:grid-cols-4 gap-2">
              <div><strong>{geoSummary.nb_nodes}</strong> nœuds</div>
              <div><strong>{geoSummary.nb_columns}</strong> poteaux</div>
              <div><strong>{geoSummary.nb_beams}</strong> poutres</div>
              <div><strong>{geoSummary.nb_supports}</strong> appuis</div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-4 w-4" /> Étape 1 — Générer le SAF pour votre logiciel
          </CardTitle>
          <CardDescription>
            Produit un fichier SAF (.xlsx) importable dans Scia Engineer, RFEM/RSTAB, Dlubal et partiellement
            Cedrus. Inclut matériaux SIA, combinaisons ELU/ELS, cas de charges.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleGenerateSaf} disabled={generating}>
            {generating ? 'Génération...' : 'Générer le SAF'}
          </Button>
          {safResult && (
            <div className="mt-4 p-4 bg-muted rounded-md space-y-2">
              <div className="flex gap-2">
                <Button asChild size="sm">
                  <a href={safResult.saf_url} target="_blank" rel="noopener noreferrer" download>
                    <Download className="h-3 w-3 mr-2" /> SAF (.xlsx)
                  </a>
                </Button>
                <Button asChild size="sm" variant="outline">
                  <a href={safResult.notice_url} target="_blank" rel="noopener noreferrer" download>
                    <Download className="h-3 w-3 mr-2" /> Notice ingénieur
                  </a>
                </Button>
              </div>
              <p className="text-xs text-muted-foreground pt-2">{safResult.next_step}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-4 w-4" /> Étape 2 — Importer les résultats et générer la note SIA
          </CardTitle>
          <CardDescription>
            Importez le SAF enrichi par votre logiciel de calcul. L'agent exécute un double-check analytique
            (vérification indépendante des ordres de grandeur) puis génère la note de calcul SIA 260-267.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>SAF enrichi (résultats du logiciel)</Label>
            <input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={(e) => setResultsFile(e.target.files?.[0] || null)}
              className="text-sm block"
            />
          </div>
          <div className="space-y-2">
            <Label>Nom de l'ingénieur</Label>
            <Input value={authorName} onChange={(e) => setAuthorName(e.target.value)} />
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={engineerValidated}
              onChange={(e) => setEngineerValidated(e.target.checked)}
              className="mt-0.5 h-4 w-4"
            />
            <span>
              <strong>Je confirme en tant qu'ingénieur qualifié</strong> avoir vérifié la géométrie du modèle,
              les cas de charges, les combinaisons, et la cohérence des résultats du logiciel. Je prends la
              responsabilité de la note qui sera générée.
            </span>
          </label>

          <Button onClick={handleImport} disabled={!resultsFile || !engineerValidated || importing}>
            <ShieldCheck className="h-4 w-4 mr-2" />
            {importing ? 'Import + double-check...' : 'Importer et générer la note SIA'}
          </Button>

          {importResult && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-md space-y-3">
              <div className="flex items-center gap-2">
                <StatusBadge
                  status={importResult.compliant ? 'CONFORME' : 'NON_CONFORME'}
                  label={importResult.compliant ? 'Conforme SIA 260-267' : 'Non conforme / à reprendre'}
                />
                <span className="text-sm text-muted-foreground">
                  Taux de travail max = {importResult.max_utilization?.toFixed(2)}
                </span>
              </div>

              <div>
                <p className="text-xs font-medium mb-1">Double-check analytique</p>
                <p className="text-xs">{importResult.double_check?.summary}</p>
                {importResult.double_check?.alerts_count > 0 && (
                  <p className="text-xs text-red-700 mt-1">
                    ⚠ {importResult.double_check.alerts_count} alerte(s) - divergence max {importResult.double_check.max_divergence_pct}%
                  </p>
                )}
              </div>

              <Button asChild>
                <a href={importResult.pdf_url} target="_blank" rel="noopener noreferrer" download>
                  <Download className="h-4 w-4 mr-2" /> Télécharger la note PDF
                </a>
              </Button>
            </div>
          )}

          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Modèle</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div><p className="text-muted-foreground">Nœuds</p><p className="font-medium">{(model.nodes || []).length}</p></div>
            <div><p className="text-muted-foreground">Éléments</p><p className="font-medium">{(model.members || []).length}</p></div>
            <div><p className="text-muted-foreground">Appuis</p><p className="font-medium">{(model.supports || []).length}</p></div>
            <div><p className="text-muted-foreground">Combinaisons</p><p className="font-medium">{(model.combinations || []).length}</p></div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Utilisez la saisie paramétrique de la trame (étape 0 ci-dessus) pour générer une géométrie
            d'avant-projet, l'import BIM (pré-BIM), ou la saisie directe dans votre logiciel après
            génération du SAF. L'édition graphique nœud-par-nœud arrivera ultérieurement.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

'use client';
import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Download, Upload, Zap, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
            Édition graphique du modèle : à venir en V2.1. Pour l'instant, utilisez l'import BIM (pré-BIM)
            ou la saisie directe dans votre logiciel de calcul après génération du SAF.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

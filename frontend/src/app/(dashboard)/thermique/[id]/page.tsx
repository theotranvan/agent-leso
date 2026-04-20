'use client';
import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Download, FileText, Upload, Zap } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge } from '@/components/swiss/StatusBadge';
import { formatDateTime } from '@/lib/utils';

export default function ThermiqueDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [model, setModel] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [engine, setEngine] = useState<'lesosai_stub' | 'lesosai_file'>('lesosai_file');
  const [authorName, setAuthorName] = useState('');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const m = await api.thermique.getModel(id);
      setModel(m);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleRun = async () => {
    setError(null);
    setRunning(true);
    try {
      const r = await api.thermique.run(id, { engine, author_name: authorName });
      setResult(r);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const handleImport = async () => {
    if (!importFile) return;
    setError(null);
    setImporting(true);
    try {
      const r = await api.thermique.importResults(id, importFile, authorName);
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
      <Link href="/thermique" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Retour
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{model.name}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {model.canton} · {model.affectation} · {model.operation_type} · {model.standard}
          </p>
        </div>
        <StatusBadge status={model.status === 'completed' ? 'CONFORME' : 'INFO'} label={model.status} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-4 w-4" />
            Étape 1 — Générer le dossier Lesosai
          </CardTitle>
          <CardDescription>
            Le moteur file produit un XML pré-rempli + une fiche de saisie pour accélérer votre travail dans Lesosai.
            Le moteur stub donne un calcul indicatif rapide (avant-projet uniquement).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Moteur</Label>
              <Select value={engine} onValueChange={(v: any) => setEngine(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="lesosai_file">Export Lesosai (production)</SelectItem>
                  <SelectItem value="lesosai_stub">Calcul indicatif rapide (avant-projet)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Nom de l'auteur / ingénieur</Label>
              <Input value={authorName} onChange={(e) => setAuthorName(e.target.value)} />
            </div>
          </div>
          <Button onClick={handleRun} disabled={running}>
            {running ? 'Génération en cours...' : 'Lancer'}
          </Button>

          {result && (
            <div className="mt-4 p-4 bg-muted rounded-md space-y-2">
              <p className="text-sm font-medium">Dossier généré</p>
              {result.lesosai_xml_url && (
                <div className="flex gap-2">
                  <Button variant="outline" asChild size="sm">
                    <a href={result.lesosai_xml_url} target="_blank" rel="noopener noreferrer" download>
                      <Download className="h-3 w-3 mr-2" /> XML Lesosai
                    </a>
                  </Button>
                  <Button variant="outline" asChild size="sm">
                    <a href={result.operator_sheet_url} target="_blank" rel="noopener noreferrer" download>
                      <Download className="h-3 w-3 mr-2" /> Fiche de saisie
                    </a>
                  </Button>
                </div>
              )}
              {result.pdf_url && (
                <Button variant="outline" asChild size="sm">
                  <a href={result.pdf_url} target="_blank" rel="noopener noreferrer" download>
                    <Download className="h-3 w-3 mr-2" /> Justificatif indicatif (PDF)
                  </a>
                </Button>
              )}
              {result.results && (
                <div className="grid grid-cols-3 gap-2 text-xs pt-2">
                  <div><strong>Qh:</strong> {result.results.qh_mj_m2_an} MJ/m²/an</div>
                  <div><strong>Qww:</strong> {result.results.qww_mj_m2_an} MJ/m²/an</div>
                  <div><strong>E:</strong> {result.results.e_mj_m2_an} MJ/m²/an</div>
                </div>
              )}
              {result.warnings && result.warnings.length > 0 && (
                <div className="text-xs text-amber-800">
                  {result.warnings.map((w: string, i: number) => <div key={i}>⚠ {w}</div>)}
                </div>
              )}
              <p className="text-xs text-muted-foreground pt-2">{result.next_step}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-4 w-4" />
            Étape 2 — Importer les résultats Lesosai officiels
          </CardTitle>
          <CardDescription>
            Après avoir lancé le calcul dans Lesosai et exporté le PDF de résultats, déposez-le ici pour
            générer le justificatif SIA 380/1 final.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              className="text-sm"
            />
            <Button onClick={handleImport} disabled={!importFile || importing}>
              {importing ? 'Import...' : 'Importer'}
            </Button>
          </div>

          {importResult && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-md space-y-2">
              <p className="text-sm font-medium text-emerald-900">Justificatif final généré</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <div><strong>Qh:</strong> {importResult.results?.qh_mj_m2_an} MJ/m²/an</div>
                <div><strong>Qww:</strong> {importResult.results?.qww_mj_m2_an}</div>
                <div><strong>E:</strong> {importResult.results?.e_mj_m2_an}</div>
                <div><strong>Qh limite:</strong> {importResult.results?.qh_limite_mj_m2_an || '?'}</div>
              </div>
              {importResult.results?.compliant !== null && (
                <StatusBadge
                  status={importResult.results?.compliant ? 'CONFORME' : 'NON_CONFORME'}
                  label={importResult.results?.compliant ? 'Conforme SIA 380/1 (Lesosai)' : 'Non conforme'}
                />
              )}
              <Button asChild>
                <a href={importResult.pdf_url} target="_blank" rel="noopener noreferrer" download>
                  <Download className="h-4 w-4 mr-2" /> Télécharger le justificatif PDF
                </a>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {error && <div className="text-sm text-destructive">{error}</div>}

      <Card>
        <CardHeader><CardTitle className="text-base">Modèle (aperçu)</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div><p className="text-muted-foreground">Zones</p><p className="font-medium">{(model.zones || []).length}</p></div>
            <div><p className="text-muted-foreground">Parois</p><p className="font-medium">{(model.walls || []).length}</p></div>
            <div><p className="text-muted-foreground">Ouvertures</p><p className="font-medium">{(model.openings || []).length}</p></div>
            <div><p className="text-muted-foreground">Ponts thermiques</p><p className="font-medium">{(model.thermal_bridges || []).length}</p></div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Édition détaillée du modèle (zones, compositions, systèmes) : à venir en V2.1. En attendant,
            la saisie complète se fait directement dans Lesosai via la fiche de saisie générée.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

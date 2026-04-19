'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Layers, Sparkles, Download, CheckCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input, Textarea } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { CantonPicker } from '@/components/swiss/CantonPicker';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AFFECTATIONS_SIA, OPERATION_TYPES } from '@/lib/ch';
import { BIMViewer } from '@/components/swiss/BIMViewer';
import { formatDate } from '@/lib/utils';

export default function BIMPage() {
  const [program, setProgram] = useState('');
  const [hints, setHints] = useState<any>({
    canton: 'GE',
    affectation: 'logement_collectif',
    operation_type: 'neuf',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [premodels, setPremodels] = useState<any[]>([]);

  const loadList = async () => {
    const d = await api.bim.listPremodels();
    setPremodels(d.premodels);
  };

  useEffect(() => { loadList(); }, []);

  const handleGenerate = async () => {
    setError(null);
    setLoading(true);
    try {
      const r = await api.bim.premodelFromText({ program_text: program, hints });
      setResult(r);
      loadList();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!result?.premodel_id) return;
    await api.bim.validate(result.premodel_id);
    loadList();
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
          <Layers className="h-6 w-6" />
          Pré-BIM
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Génération automatique d'un pré-modèle IFC depuis un programme architectural.
          Bâtiments orthogonaux simples (V2).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Générer un pré-modèle</CardTitle>
          <CardDescription>
            Collez le programme / cahier des charges. L'IA extrait les étages, surfaces,
            hauteurs puis génère un IFC 4 exploitable par vos outils BIM.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Canton</Label>
              <CantonPicker value={hints.canton} onChange={(c) => setHints({ ...hints, canton: c })} includeAll={false} />
            </div>
            <div className="space-y-2">
              <Label>Affectation</Label>
              <Select value={hints.affectation} onValueChange={(v) => setHints({ ...hints, affectation: v })}>
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
              <Select value={hints.operation_type} onValueChange={(v) => setHints({ ...hints, operation_type: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {OPERATION_TYPES.map((o) => (
                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Programme architectural</Label>
            <Textarea
              rows={10}
              placeholder="Exemple :&#10;Résidence Les Acacias, 6 logements sur 3 étages (Rez + R+1 + R+2), surface de plancher 250 m² par étage, hauteur d'étage 2.8 m, dimensions approximatives 25 x 10 m, construction neuve performante ISO 50 cm d'isolation, fenêtres 30% façade sud..."
              value={program}
              onChange={(e) => setProgram(e.target.value)}
            />
          </div>

          <Button onClick={handleGenerate} disabled={!program.trim() || loading}>
            <Sparkles className="h-4 w-4 mr-2" />
            {loading ? 'Génération...' : 'Générer le pré-modèle'}
          </Button>

          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      {result && (
        <>
          <BIMViewer
            ifcUrl={result.ifc_url}
            report={result.report}
            onValidate={handleValidate}
          />

          {result.spec && (
            <Card>
              <CardHeader><CardTitle className="text-base">Spec générée (JSON)</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-64">
                  {JSON.stringify(result.spec, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Card>
        <CardHeader><CardTitle>Pré-modèles précédents</CardTitle></CardHeader>
        <CardContent>
          {premodels.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun pré-modèle encore.</p>
          ) : (
            <ul className="divide-y">
              {premodels.map((p) => (
                <li key={p.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{p.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(p.created_at)} · confiance {Math.round((p.generation_report?.confidence || 0) * 100)}%
                      {p.validated && ' · ✓ validé'}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

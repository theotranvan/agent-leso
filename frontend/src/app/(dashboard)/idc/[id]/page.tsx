'use client';
import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Download, Plus, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge } from '@/components/swiss/StatusBadge';
import { AFFECTATIONS_IDC } from '@/lib/ch';
import { formatDate } from '@/lib/utils';

const DJU_NORMAL_GE = 3050;

type Invoice = {
  value: string;
  unit: string;
  period_start: string;
  period_end: string;
  source_document_id?: string | null;
  filename?: string;
  confidence?: number | null;
};

export default function IDCDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [building, setBuilding] = useState<any>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
  const [dju, setDju] = useState<string>(String(DJU_NORMAL_GE));
  const [affectation, setAffectation] = useState<string>('logement_collectif');
  const [affectationTouched, setAffectationTouched] = useState(false);
  const [creating, setCreating] = useState(false);
  const [declaration, setDeclaration] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const b = await api.idc.getBuilding(id);
      setBuilding(b);
      // Défaut d'affectation déduit du nombre de logements, tant que non modifié à la main.
      if (!affectationTouched) {
        setAffectation((b.nb_logements || 0) > 1 ? 'logement_collectif' : 'logement_individuel');
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleInvoiceUpload = async (file: File) => {
    setError(null);
    try {
      const result = await api.idc.extractInvoice(id, file);
      const ex = result.extracted || {};
      setInvoices((prev) => [
        ...prev,
        {
          value: ex.value != null ? String(ex.value) : '',
          unit: ex.unit || '',
          period_start: ex.period_start || '',
          period_end: ex.period_end || '',
          source_document_id: result.source_document_id,
          filename: file.name,
          confidence: ex.confidence ?? null,
        },
      ]);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const updateInvoice = (idx: number, field: keyof Invoice, value: string) => {
    setInvoices((prev) => prev.map((inv, i) => (i === idx ? { ...inv, [field]: value } : inv)));
  };
  const removeInvoice = (idx: number) => setInvoices((prev) => prev.filter((_, i) => i !== idx));
  const addManualInvoice = () =>
    setInvoices((prev) => [...prev, { value: '', unit: '', period_start: '', period_end: '', filename: 'Saisie manuelle', confidence: null }]);

  const handleCreateDeclaration = async () => {
    setError(null);
    setCreating(true);
    try {
      const payload = {
        building_id: id,
        year,
        affectation,
        dju_year: dju ? Number(dju) : null,
        invoices: invoices
          .filter((i) => Number(i.value) > 0)
          .map((i) => ({
            value: Number(i.value),
            unit: i.unit || 'kwh',
            period_start: i.period_start || null,
            period_end: i.period_end || null,
            source_document_id: i.source_document_id || null,
          })),
      };
      const r = await api.idc.createDeclaration(payload);
      setDeclaration(r);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  if (!building) return <div className="text-muted-foreground">Chargement...</div>;

  return (
    <div className="space-y-6 max-w-5xl">
      <Link href="/idc" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4 mr-1" /> Retour
      </Link>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{building.address}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          EGID {building.ega || '—'} · SRE {building.sre_m2} m² · {building.heating_energy_vector}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Nouvelle déclaration annuelle</CardTitle>
          <CardDescription>
            Téléversez les factures chaufferie de l'année (extraction automatique), corrigez si besoin,
            renseignez le DJU de l'année et l'affectation. L'IDC est normalisé au climat puis classé.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Année de déclaration</Label>
              <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </div>
            <div className="space-y-2">
              <Label>DJU de l'année (Genève-Cointrin)</Label>
              <Input type="number" value={dju} onChange={(e) => setDju(e.target.value)} />
              <p className="text-[11px] text-muted-foreground">
                Normal = {DJU_NORMAL_GE}. Saisir les DJU réels de l'année (source OCEN / MétéoSuisse) pour la correction climatique.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Affectation</Label>
              <Select value={affectation} onValueChange={(v) => { setAffectation(v); setAffectationTouched(true); }}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {AFFECTATIONS_IDC.map((a) => (
                    <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Factures de chauffage (PDF)</Label>
              <Button variant="outline" size="sm" onClick={addManualInvoice}>
                <Plus className="h-3 w-3 mr-1" /> Saisie manuelle
              </Button>
            </div>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) handleInvoiceUpload(f);
                e.target.value = '';
              }}
              className="block text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Plusieurs factures possibles. Les valeurs extraites sont éditables ci-dessous — corrigez avant de calculer.
            </p>
          </div>

          {invoices.length > 0 && (
            <div className="border rounded-md overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-2">Source</th>
                    <th className="text-left p-2">Valeur</th>
                    <th className="text-left p-2">Unité</th>
                    <th className="text-left p-2">Début</th>
                    <th className="text-left p-2">Fin</th>
                    <th className="text-left p-2">Conf.</th>
                    <th className="p-2" />
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-1 text-xs max-w-[120px] truncate" title={inv.filename}>{inv.filename}</td>
                      <td className="p-1">
                        <Input className="h-8 w-24" type="number" value={inv.value}
                          onChange={(e) => updateInvoice(i, 'value', e.target.value)} />
                      </td>
                      <td className="p-1">
                        <Input className="h-8 w-20" placeholder="kwh/litre/m3" value={inv.unit}
                          onChange={(e) => updateInvoice(i, 'unit', e.target.value)} />
                      </td>
                      <td className="p-1">
                        <Input className="h-8 w-36" type="date" value={inv.period_start}
                          onChange={(e) => updateInvoice(i, 'period_start', e.target.value)} />
                      </td>
                      <td className="p-1">
                        <Input className="h-8 w-36" type="date" value={inv.period_end}
                          onChange={(e) => updateInvoice(i, 'period_end', e.target.value)} />
                      </td>
                      <td className="p-1">
                        {inv.confidence != null ? (
                          <StatusBadge
                            status={inv.confidence > 0.7 ? 'OK' : inv.confidence > 0.4 ? 'ATTENTION' : 'CRITIQUE'}
                            label={`${Math.round((inv.confidence || 0) * 100)}%`}
                          />
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="p-1">
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => removeInvoice(i)}>
                          <Trash2 className="h-3 w-3 text-muted-foreground" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Button onClick={handleCreateDeclaration} disabled={invoices.filter((i) => Number(i.value) > 0).length === 0 || creating}>
            {creating ? 'Calcul en cours...' : 'Calculer et générer le formulaire IDC'}
          </Button>

          {declaration && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-md space-y-2">
              <p className="text-sm font-medium">Déclaration {declaration.year} générée</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">IDC normalisé</p>
                  <p className="text-lg font-bold">{declaration.calc?.idc_normalise_mj_m2} MJ/m²/an</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">IDC brut</p>
                  <p className="text-sm font-medium">{declaration.calc?.idc_brut_mj_m2} MJ/m²/an</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Correction climat</p>
                  <p className="text-sm font-medium">×{declaration.calc?.correction_factor ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Statut</p>
                  <StatusBadge
                    status={declaration.calc?.status?.level || 'INFO'}
                    label={declaration.calc?.status?.label}
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Seuil « dans la cible » : {declaration.calc?.seuil_ok_mj_m2} MJ/m²/an ·
                Seuil assainissement : {declaration.calc?.seuil_assainissement_mj_m2} MJ/m²/an
              </p>
              {declaration.calc?.warnings?.length > 0 && (
                <div className="text-xs text-amber-800">
                  {declaration.calc.warnings.map((w: string, i: number) => <div key={i}>⚠ {w}</div>)}
                </div>
              )}
              <Button asChild size="sm">
                <a href={declaration.pdf_url} target="_blank" rel="noopener noreferrer" download>
                  <Download className="h-3 w-3 mr-2" /> Télécharger le formulaire PDF
                </a>
              </Button>
            </div>
          )}

          {error && <div className="text-sm text-destructive">{error}</div>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Historique des déclarations</CardTitle></CardHeader>
        <CardContent>
          {!building.declarations || building.declarations.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune déclaration pour ce bâtiment.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left p-2">Année</th>
                  <th className="text-left p-2">IDC (MJ/m²/an)</th>
                  <th className="text-left p-2">Conso (kWh)</th>
                  <th className="text-left p-2">Statut</th>
                  <th className="text-left p-2">Créée</th>
                </tr>
              </thead>
              <tbody>
                {building.declarations.map((d: any) => (
                  <tr key={d.id} className="border-t">
                    <td className="p-2 font-medium">{d.year}</td>
                    <td className="p-2">{d.idc_mj_m2 || '—'}</td>
                    <td className="p-2">{d.consumption_kwh?.toLocaleString('fr-CH') || '—'}</td>
                    <td className="p-2"><StatusBadge status={d.status} /></td>
                    <td className="p-2 text-xs">{formatDate(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

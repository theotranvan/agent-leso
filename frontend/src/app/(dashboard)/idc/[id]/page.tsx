'use client';
import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Plus, Upload, Download, FileText } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { StatusBadge } from '@/components/swiss/StatusBadge';
import { formatDate } from '@/lib/utils';

export default function IDCDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [building, setBuilding] = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [year, setYear] = useState<number>(new Date().getFullYear() - 1);
  const [creating, setCreating] = useState(false);
  const [declaration, setDeclaration] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const b = await api.idc.getBuilding(id);
      setBuilding(b);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, [id]);

  const handleInvoiceUpload = async (file: File) => {
    setError(null);
    try {
      const result = await api.idc.extractInvoice(id, file);
      setInvoices((prev) => [
        ...prev,
        {
          ...result.extracted,
          source_document_id: result.source_document_id,
          filename: file.name,
        },
      ]);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleCreateDeclaration = async () => {
    setError(null);
    setCreating(true);
    try {
      const r = await api.idc.createDeclaration({
        building_id: id,
        year,
        invoices: invoices.filter((i) => i.value),
      });
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
            Téléversez les factures chaufferie de l'année considérée. L'agent extrait les consommations
            puis calcule l'IDC normalisé en MJ/m²/an.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Année de déclaration</Label>
              <Input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Factures de chauffage (PDF)</Label>
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
              Vous pouvez uploader plusieurs factures successivement. Chaque upload extrait automatiquement la consommation.
            </p>
          </div>

          {invoices.length > 0 && (
            <div className="border rounded-md">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-2">Facture</th>
                    <th className="text-left p-2">Valeur</th>
                    <th className="text-left p-2">Unité</th>
                    <th className="text-left p-2">Période</th>
                    <th className="text-left p-2">Confiance</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv, i) => (
                    <tr key={i} className="border-t">
                      <td className="p-2 text-xs">{inv.filename}</td>
                      <td className="p-2">{inv.value || '?'}</td>
                      <td className="p-2">{inv.unit || '?'}</td>
                      <td className="p-2 text-xs">
                        {inv.period_start && inv.period_end
                          ? `${inv.period_start} → ${inv.period_end}`
                          : '—'}
                      </td>
                      <td className="p-2">
                        <StatusBadge
                          status={inv.confidence > 0.7 ? 'OK' : inv.confidence > 0.4 ? 'ATTENTION' : 'CRITIQUE'}
                          label={`${Math.round((inv.confidence || 0) * 100)}%`}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Button onClick={handleCreateDeclaration} disabled={invoices.length === 0 || creating}>
            {creating ? 'Calcul en cours...' : 'Calculer et générer le formulaire IDC'}
          </Button>

          {declaration && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-md space-y-2">
              <p className="text-sm font-medium">Déclaration {declaration.year} générée</p>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">IDC normalisé</p>
                  <p className="text-lg font-bold">{declaration.calc?.idc_normalise_mj_m2} MJ/m²/an</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Énergie annuelle</p>
                  <p className="text-sm font-medium">{declaration.calc?.consumption_kwh?.toLocaleString('fr-CH')} kWh</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Statut</p>
                  <StatusBadge
                    status={declaration.calc?.status?.level || 'INFO'}
                    label={declaration.calc?.status?.label}
                  />
                </div>
              </div>
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

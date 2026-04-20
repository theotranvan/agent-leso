'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Download, CheckCircle2, AlertTriangle, Save, Flame, Loader2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/swiss/StatusBadge';
import { formatDateTime } from '@/lib/utils';

type ChecklistItem = {
  code: string;
  category: string;
  question: string;
  answer?: string | boolean | null;
  comment?: string;
  status?: 'conforme' | 'non_conforme' | 'a_verifier' | 'na';
};

type Checklist = {
  id: string;
  building_type: string;
  status: string;
  items: ChecklistItem[];
  height_m?: number | null;
  nb_occupants_max?: number | null;
  created_at: string;
  updated_at?: string;
};

export default function AEAIDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const data = await api.aeai.getChecklist(id);
      setChecklist(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const handleItemChange = (idx: number, field: keyof ChecklistItem, value: any) => {
    if (!checklist) return;
    const updated = { ...checklist };
    updated.items = [...updated.items];
    updated.items[idx] = { ...updated.items[idx], [field]: value };
    setChecklist(updated);
  };

  const handleSave = async () => {
    if (!checklist) return;
    setSaving(true);
    setError(null);
    try {
      await api.aeai.updateChecklist(id, { items: checklist.items });
      setSavedAt(new Date().toISOString());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const res = await api.aeai.exportPDF(id);
      if (res.pdf_url) {
        window.open(res.pdf_url, '_blank');
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setExporting(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      await api.aeai.updateChecklist(id, { status: 'validated' });
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground p-6">
        <Loader2 className="h-4 w-4 animate-spin" /> Chargement...
      </div>
    );
  }

  if (error && !checklist) {
    return (
      <div className="p-6">
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!checklist) return null;

  // Regroupement par catégorie
  const itemsByCategory = checklist.items.reduce<Record<string, { item: ChecklistItem; idx: number }[]>>(
    (acc, item, idx) => {
      const cat = item.category || 'Général';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push({ item, idx });
      return acc;
    },
    {},
  );

  // Stats
  const total = checklist.items.length;
  const conforme = checklist.items.filter((i) => i.status === 'conforme').length;
  const nonConforme = checklist.items.filter((i) => i.status === 'non_conforme').length;
  const aVerifier = checklist.items.filter((i) => i.status === 'a_verifier').length;
  const completion = total > 0 ? Math.round((conforme + nonConforme) / total * 100) : 0;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href="/aeai" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 mb-2">
            <ArrowLeft className="h-3 w-3" /> Retour aux checklists
          </Link>
          <div className="flex items-center gap-3 mb-1">
            <Flame className="h-5 w-5 text-orange-600" />
            <h1 className="text-2xl font-semibold">Checklist AEAI</h1>
            <StatusBadge status={checklist.status as any} />
          </div>
          <p className="text-sm text-muted-foreground">
            Typologie : <span className="text-foreground font-medium">{checklist.building_type}</span>
            {checklist.height_m && <> · Hauteur {checklist.height_m} m</>}
            {checklist.nb_occupants_max && <> · {checklist.nb_occupants_max} occupants max</>}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Créée le {formatDateTime(checklist.created_at)}
            {savedAt && <> · Sauvegardée à {formatDateTime(savedAt)}</>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportPDF} disabled={exporting}>
            {exporting ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-2" /> : <Download className="h-3.5 w-3.5 mr-2" />}
            Export PDF
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-2" /> : <Save className="h-3.5 w-3.5 mr-2" />}
            Enregistrer
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-3">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1">Total points</div>
            <div className="text-2xl font-semibold">{total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1">Conformes</div>
            <div className="text-2xl font-semibold text-emerald-600">{conforme}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1">Non conformes</div>
            <div className="text-2xl font-semibold text-red-600">{nonConforme}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-muted-foreground mb-1">À vérifier</div>
            <div className="text-2xl font-semibold text-amber-600">{aVerifier}</div>
          </CardContent>
        </Card>
      </div>

      {/* Progress */}
      <div>
        <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
          <span>Avancement</span>
          <span>{completion}%</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary transition-all"
            style={{ width: `${completion}%` }}
          />
        </div>
      </div>

      {/* Items par catégorie */}
      <div className="space-y-4">
        {Object.entries(itemsByCategory).map(([category, entries]) => (
          <Card key={category}>
            <CardHeader>
              <CardTitle className="text-base">{category}</CardTitle>
              <CardDescription>
                {entries.filter((e) => e.item.status === 'conforme').length} / {entries.length} conformes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {entries.map(({ item, idx }) => (
                <div key={item.code} className="rounded-md border p-3 space-y-2">
                  <div className="flex items-start gap-2">
                    <Badge variant="outline" className="font-mono text-xs shrink-0">
                      {item.code}
                    </Badge>
                    <p className="text-sm leading-relaxed flex-1">{item.question}</p>
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    {(['conforme', 'non_conforme', 'a_verifier', 'na'] as const).map((st) => (
                      <Button
                        key={st}
                        size="sm"
                        variant={item.status === st ? 'default' : 'outline'}
                        className="text-xs h-7 px-2"
                        onClick={() => handleItemChange(idx, 'status', st)}
                      >
                        {st === 'conforme' && '✓ Conforme'}
                        {st === 'non_conforme' && '✗ Non conforme'}
                        {st === 'a_verifier' && '? À vérifier'}
                        {st === 'na' && 'N/A'}
                      </Button>
                    ))}
                  </div>

                  <Textarea
                    placeholder="Commentaire / référence / observation..."
                    value={item.comment || ''}
                    onChange={(e) => handleItemChange(idx, 'comment', e.target.value)}
                    className="text-sm min-h-[60px]"
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Validation footer */}
      {checklist.status !== 'validated' && (
        <Card className="border-emerald-200 bg-emerald-50/30">
          <CardContent className="pt-6 flex items-center justify-between gap-4">
            <div className="text-sm">
              <p className="font-medium">Prêt à valider cette checklist ?</p>
              <p className="text-muted-foreground mt-1">
                Une fois validée, elle sera marquée comme finalisée. Vous pourrez toujours l'exporter.
              </p>
            </div>
            <Button onClick={handleValidate} disabled={validating || nonConforme > 0}>
              {validating ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-2" /> : <CheckCircle2 className="h-3.5 w-3.5 mr-2" />}
              Valider la checklist
            </Button>
          </CardContent>
        </Card>
      )}

      <p className="text-xs text-muted-foreground italic pt-2">
        Référence : directives AEAI. Ne remplace ni l'avis d'un expert incendie ni la procédure d'approbation
        selon l'autorité compétente.
      </p>
    </div>
  );
}

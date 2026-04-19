'use client';
import { useEffect, useState } from 'react';
import { Flame, Plus, Download, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/input';
import { AEAI_BUILDING_TYPES } from '@/lib/ch';
import { StatusBadge } from '@/components/swiss/StatusBadge';
import { formatDate } from '@/lib/utils';

export default function AEAIPage() {
  const [checklists, setChecklists] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<any>({
    building_type: 'habitation_faible',
    height_m: '',
    nb_occupants_max: '',
  });
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const d = await api.aeai.listChecklists();
    setChecklists(d.checklists);
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const data = {
        building_type: form.building_type,
        height_m: form.height_m ? Number(form.height_m) : null,
        nb_occupants_max: form.nb_occupants_max ? Number(form.nb_occupants_max) : null,
      };
      const r = await api.aeai.createChecklist(data);
      setActive(r);
      setCreating(false);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleItemUpdate = async (idx: number, field: string, value: any) => {
    if (!active) return;
    const items = [...active.items];
    items[idx] = { ...items[idx], [field]: value };
    setActive({ ...active, items });
  };

  const handleSave = async () => {
    if (!active) return;
    await api.aeai.updateChecklist(active.id, { items: active.items });
    load();
  };

  const handleExportPdf = async () => {
    if (!active) return;
    await handleSave();
    const r = await api.aeai.exportPdf(active.id);
    window.open(r.pdf_url, '_blank');
  };

  const handleValidate = async () => {
    if (!active) return;
    await handleSave();
    await api.aeai.updateChecklist(active.id, { status: 'validated' });
    load();
    setActive({ ...active, status: 'validated' });
  };

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Flame className="h-6 w-6" />
            Checklists AEAI (incendie)
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Pré-remplissage automatique par typologie selon prescriptions AEAI 2015
          </p>
        </div>
        <Button onClick={() => setCreating(!creating)}>
          <Plus className="h-4 w-4 mr-2" /> Nouvelle checklist
        </Button>
      </div>

      {creating && (
        <Card>
          <CardHeader><CardTitle>Nouvelle checklist AEAI</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid md:grid-cols-3 gap-4">
                <div className="space-y-2 md:col-span-2">
                  <Label>Typologie</Label>
                  <Select value={form.building_type} onValueChange={(v) => setForm({ ...form, building_type: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {AEAI_BUILDING_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Hauteur (m)</Label>
                  <Input
                    type="number"
                    value={form.height_m}
                    onChange={(e) => setForm({ ...form, height_m: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Occupation maximale</Label>
                  <Input
                    type="number"
                    value={form.nb_occupants_max}
                    onChange={(e) => setForm({ ...form, nb_occupants_max: e.target.value })}
                  />
                </div>
              </div>
              {error && <div className="text-sm text-destructive">{error}</div>}
              <div className="flex gap-2">
                <Button type="submit">Créer</Button>
                <Button type="button" variant="outline" onClick={() => setCreating(false)}>Annuler</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {active && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Checklist {active.building_type}</CardTitle>
                <CardDescription>{active.items?.length || 0} points à vérifier</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleSave}>Enregistrer</Button>
                <Button variant="outline" size="sm" onClick={handleExportPdf}>
                  <Download className="h-3 w-3 mr-2" /> Export PDF
                </Button>
                <Button size="sm" onClick={handleValidate}>
                  <CheckCircle2 className="h-3 w-3 mr-2" /> Valider
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(active.items || []).map((item: any, idx: number) => (
                <div key={item.id || idx} className="border rounded-md p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-muted-foreground">{item.reference}</span>
                        <StatusBadge status={item.severity} />
                      </div>
                      <p className="text-sm font-medium">{item.title}</p>
                      {item.description && (
                        <p className="text-xs text-muted-foreground mt-1">{item.description}</p>
                      )}
                    </div>
                    <Select
                      value={item.status}
                      onValueChange={(v) => handleItemUpdate(idx, 'status', v)}
                    >
                      <SelectTrigger className="w-40 shrink-0">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="A_VERIFIER">À vérifier</SelectItem>
                        <SelectItem value="CONFORME">Conforme</SelectItem>
                        <SelectItem value="NON_CONFORME">Non conforme</SelectItem>
                        <SelectItem value="NON_APPLICABLE">N/A</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="mt-2">
                    <Textarea
                      rows={1}
                      placeholder="Note..."
                      value={item.notes || ''}
                      onChange={(e) => handleItemUpdate(idx, 'notes', e.target.value)}
                      className="text-xs"
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Checklists existantes</CardTitle></CardHeader>
        <CardContent>
          {checklists.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune checklist.</p>
          ) : (
            <ul className="divide-y">
              {checklists.map((c) => (
                <li key={c.id} className="py-3">
                  <button
                    onClick={() => setActive(c)}
                    className="w-full flex items-center justify-between text-left hover:bg-accent -mx-2 px-2 rounded-md"
                  >
                    <div>
                      <p className="text-sm font-medium">{c.building_type}</p>
                      <p className="text-xs text-muted-foreground">
                        {(c.items || []).length} points · {formatDate(c.created_at)}
                      </p>
                    </div>
                    <StatusBadge status={c.status === 'validated' ? 'CONFORME' : 'INFO'} label={c.status} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

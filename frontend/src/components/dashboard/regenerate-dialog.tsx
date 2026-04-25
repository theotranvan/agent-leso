'use client';
import { useEffect, useState } from 'react';
import { X, Loader2, Zap, AlertCircle, ChevronDown, Check } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Banner } from '@/components/ui/banner';

export const MAX_REGENERATIONS = 5;

// Motifs pré-codés — doivent matcher backend VALID_REGENERATION_REASONS
export const REGENERATION_REASONS: { code: string; label: string; description: string }[] = [
  { code: 'too_generic',     label: 'Trop générique',        description: "Manque de spécificité projet" },
  { code: 'wrong_norm',      label: 'Mauvaise norme',        description: "Norme citée incorrecte ou mal référencée" },
  { code: 'missing_info',    label: 'Infos manquantes',      description: "Sections ou données importantes omises" },
  { code: 'wrong_tone',      label: 'Ton inapproprié',       description: "Trop marketing, trop sec, pas assez pro" },
  { code: 'factual_error',   label: 'Erreur factuelle',      description: "Valeur, calcul ou référence incorrect" },
  { code: 'wrong_structure', label: 'Structure à revoir',    description: "Plan du document à réorganiser" },
  { code: 'too_long',        label: 'Trop long',             description: "Trop détaillé, à condenser" },
  { code: 'too_short',       label: 'Trop court',            description: "Manque de profondeur technique" },
  { code: 'language_issue',  label: 'Langue',                description: "Français maladroit, fautes, anglicismes" },
  { code: 'assumption_wrong',label: 'Hypothèse invalide',    description: "Hypothèse posée non valable ici" },
  { code: 'citation_missing',label: 'Références manquantes', description: "Sources / normes insuffisamment citées" },
  { code: 'other',           label: 'Autre',                 description: "Précise dans le commentaire ci-dessous" },
];

interface RegenerateDialogProps {
  taskId: string;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  currentPreview?: string;
  regenerationCount?: number;
}

export function RegenerateDialog({
  taskId, open, onClose, onSuccess, currentPreview, regenerationCount = 0,
}: RegenerateDialogProps) {
  const [reasons, setReasons] = useState<Set<string>>(new Set());
  const [customFeedback, setCustomFeedback] = useState('');
  const [targetSections, setTargetSections] = useState('');
  const [upgradeModel, setUpgradeModel] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form quand on ferme
  useEffect(() => {
    if (!open) {
      setReasons(new Set());
      setCustomFeedback('');
      setTargetSections('');
      setUpgradeModel(false);
      setError(null);
    }
  }, [open]);

  // Escape key
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', h);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', h);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  if (!open) return null;

  const remaining = Math.max(0, MAX_REGENERATIONS - regenerationCount);
  const atLimit = remaining === 0;

  const toggleReason = (code: string) => {
    const next = new Set(reasons);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    setReasons(next);
  };

  const canSubmit = !submitting && !atLimit && (reasons.size > 0 || customFeedback.trim().length > 0);

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const sections = targetSections
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean);

      await api.regenerateTask(taskId, {
        reasons: Array.from(reasons),
        custom_feedback: customFeedback.trim(),
        target_sections: sections,
        upgrade_model: upgradeModel,
      });

      onSuccess?.();
      onClose();
    } catch (e: any) {
      // Parse du message 402 quota ou 429 limite
      const msg = e?.message || 'Erreur lors de la régénération';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-[2px] z-40 animate-in fade-in duration-150"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div className="pointer-events-auto bg-card rounded-lg border shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-in zoom-in-95 duration-150">
          {/* Header */}
          <div className="flex items-start justify-between px-5 py-4 border-b">
            <div>
              <h2 className="font-medium text-base flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                Régénérer la tâche
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                Dis-nous ce qui ne va pas — l'agent corrigera précisément ces points.
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md hover:bg-muted transition-colors"
              aria-label="Fermer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {/* Compteur régénérations */}
            <div className={`text-xs rounded-md px-3 py-2 border flex items-center gap-2 ${
              atLimit ? 'bg-red-50 border-red-200 text-red-800' :
              remaining <= 2 ? 'bg-amber-50 border-amber-200 text-amber-800' :
              'bg-muted/50 border-border text-muted-foreground'
            }`}>
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {atLimit ? (
                <span>
                  Limite atteinte : {MAX_REGENERATIONS} régénérations par tâche.
                  Crée une nouvelle tâche avec des inputs révisés.
                </span>
              ) : (
                <span>
                  {regenerationCount} régénération{regenerationCount > 1 ? 's' : ''} déjà effectuée{regenerationCount > 1 ? 's' : ''}.
                  Il en reste <strong>{remaining}</strong> sur {MAX_REGENERATIONS}.
                </span>
              )}
            </div>

            {error && <Banner variant="error">{error}</Banner>}

            {/* Motifs */}
            <div>
              <p className="text-sm font-medium mb-2">Qu'est-ce qui ne va pas ?</p>
              <p className="text-xs text-muted-foreground mb-3">
                Coche tout ce qui s'applique (au moins un, ou un commentaire libre)
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {REGENERATION_REASONS.map((r) => {
                  const checked = reasons.has(r.code);
                  return (
                    <button
                      key={r.code}
                      type="button"
                      onClick={() => toggleReason(r.code)}
                      disabled={atLimit}
                      className={`flex items-start gap-2 text-left rounded-md border p-2.5 text-sm transition-colors ${
                        checked
                          ? 'border-primary bg-primary/5'
                          : 'hover:border-muted-foreground/40 hover:bg-muted/30'
                      } ${atLimit ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className={`mt-0.5 h-4 w-4 rounded border grid place-items-center shrink-0 transition-colors ${
                        checked ? 'bg-primary border-primary' : 'border-muted-foreground/40'
                      }`}>
                        {checked && <Check className="h-3 w-3 text-primary-foreground" strokeWidth={3} />}
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium text-xs leading-tight">{r.label}</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5 leading-tight">
                          {r.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Feedback libre */}
            <div>
              <label className="text-sm font-medium mb-1.5 block">
                Commentaire libre <span className="text-muted-foreground font-normal">(optionnel)</span>
              </label>
              <Textarea
                value={customFeedback}
                onChange={(e) => setCustomFeedback(e.target.value)}
                placeholder="Précisions : ce qui doit changer, ce qui était correct à conserver, etc."
                rows={3}
                maxLength={2000}
                disabled={atLimit}
              />
              <p className="text-[11px] text-muted-foreground mt-1 text-right">
                {customFeedback.length}/2000
              </p>
            </div>

            {/* Sections ciblées */}
            <details className="group">
              <summary className="flex items-center gap-1.5 cursor-pointer text-sm font-medium py-1 -mx-1 px-1 rounded hover:bg-muted/40">
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform group-open:rotate-180" />
                Options avancées
              </summary>
              <div className="pt-3 space-y-4 pl-5">
                <div>
                  <label className="text-sm font-medium mb-1.5 block">
                    Sections à retravailler en priorité
                  </label>
                  <p className="text-xs text-muted-foreground mb-2">
                    Une section par ligne. Vide = régénération complète.<br />
                    Ex : <code className="text-[11px] bg-muted px-1 rounded">3. Enveloppe thermique</code>
                  </p>
                  <Textarea
                    value={targetSections}
                    onChange={(e) => setTargetSections(e.target.value)}
                    placeholder={'3. Enveloppe thermique\n5. Conformité SIA 380/1'}
                    rows={3}
                    disabled={atLimit}
                  />
                </div>

                <label className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={upgradeModel}
                    onChange={(e) => setUpgradeModel(e.target.checked)}
                    disabled={atLimit}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium">Utiliser un modèle plus puissant</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Haiku → Sonnet → Opus selon le niveau actuel.
                      Consomme plus de tokens.
                    </p>
                  </div>
                </label>
              </div>
            </details>

            {/* Aperçu version actuelle */}
            {currentPreview && (
              <details className="group">
                <summary className="flex items-center gap-1.5 cursor-pointer text-sm font-medium py-1 -mx-1 px-1 rounded hover:bg-muted/40">
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform group-open:rotate-180" />
                  Voir l'aperçu de la version actuelle
                </summary>
                <div className="pt-3 pl-5">
                  <div className="rounded-md bg-muted/40 p-3 max-h-48 overflow-y-auto">
                    <pre className="text-[11px] font-mono leading-relaxed whitespace-pre-wrap text-muted-foreground">
                      {currentPreview.slice(0, 1500)}
                      {currentPreview.length >= 1500 && '…'}
                    </pre>
                  </div>
                </div>
              </details>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t bg-muted/20">
            <Button variant="ghost" onClick={onClose} disabled={submitting}>
              Annuler
            </Button>
            <Button onClick={handleSubmit} disabled={!canSubmit} className="gap-2">
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Envoi…
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Lancer la régénération
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

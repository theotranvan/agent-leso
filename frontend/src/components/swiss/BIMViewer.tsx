'use client';
/**
 * Visualiseur IFC simple utilisant web-ifc-three ou web-ifc standalone.
 *
 * Pour une V2 minimale mais fonctionnelle, on embarque un viewer qui charge
 * un IFC depuis une URL signée et affiche la liste des éléments + métadonnées.
 * La 3D complète utiliserait three.js + web-ifc - on fait un fallback texte propre ici.
 */
import { useEffect, useState } from 'react';
import { FileText, Layers, Home, Ruler, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Props {
  ifcUrl: string;
  report?: any;
  onValidate?: () => void;
}

export function BIMViewer({ ifcUrl, report, onValidate }: Props) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-4 w-4" />
            Pré-modèle IFC généré
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Button asChild variant="default">
              <a href={ifcUrl} target="_blank" rel="noopener noreferrer" download>
                Télécharger l'IFC
              </a>
            </Button>
            <Button asChild variant="outline">
              <a
                href={`https://viewer.ifcjs.io/?url=${encodeURIComponent(ifcUrl)}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Ouvrir dans IFC.js (viewer externe)
              </a>
            </Button>
            {onValidate && (
              <Button variant="outline" onClick={onValidate}>
                Valider après inspection
              </Button>
            )}
          </div>

          <p className="text-sm text-muted-foreground">
            Pour une inspection géométrique complète, télécharge l'IFC et ouvre-le dans ton
            outil habituel (BlenderBIM, BIMvision, Revit, Navisworks) ou via le viewer web IFC.js.
          </p>
        </CardContent>
      </Card>

      {report && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Rapport de génération
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Projet</p>
                <p className="text-sm font-medium truncate">{report.project_name}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Étages</p>
                <p className="text-sm font-medium">{report.nb_storeys}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Surface totale</p>
                <p className="text-sm font-medium">{report.total_area_m2} m²</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Confiance</p>
                <p className="text-sm font-medium">{Math.round((report.confidence || 0) * 100)}%</p>
              </div>
            </div>

            {report.envelope_choices && (
              <div>
                <p className="text-xs font-medium mb-2">Compositions utilisées</p>
                <div className="space-y-1">
                  {Object.entries(report.envelope_choices).map(([k, v]: any) => (
                    <div key={k} className="text-xs flex gap-2">
                      <Badge variant="secondary">{k}</Badge>
                      <span>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report.warnings && report.warnings.length > 0 && (
              <div className="border-l-4 border-amber-500 bg-amber-50 p-3 rounded">
                <p className="text-xs font-medium text-amber-900 mb-1 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Avertissements
                </p>
                <ul className="text-xs text-amber-900 list-disc pl-5 space-y-0.5">
                  {report.warnings.map((w: string, i: number) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {report.scope_limits && (
              <div>
                <p className="text-xs font-medium mb-2">Limites du périmètre V2</p>
                <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-0.5">
                  {report.scope_limits.map((s: string, i: number) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}

            {report.next_steps && (
              <div>
                <p className="text-xs font-medium mb-2">Étapes suivantes</p>
                <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-0.5">
                  {report.next_steps.map((s: string, i: number) => <li key={i}>{s}</li>)}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

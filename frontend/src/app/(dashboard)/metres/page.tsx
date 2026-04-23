'use client';
import { useState, useRef } from 'react';
import { Calculator, Loader2, Download, AlertCircle, Upload, FileSpreadsheet } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function MetresPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState('');
  const [author, setAuthor] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExtract = async () => {
    if (!file) {
      setError('Sélectionnez un fichier IFC');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('ifc_file', file);
      fd.append('project_name', projectName);
      fd.append('author', author);
      const r = await api.v4.metres.extract(fd);
      setResult(r);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Calculator className="h-6 w-6 text-teal-600" />
        <div>
          <h1 className="text-2xl font-semibold">Métrés automatiques depuis IFC</h1>
          <p className="text-sm text-muted-foreground">
            Extraction SIA 416 + DPGF pré-rempli par CFC en quelques secondes
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Fichier IFC</CardTitle>
          <CardDescription>
            Upload d'un IFC 2x3 ou IFC 4. Plus il contient de Pset / BaseQuantities,
            plus les métrés seront précis.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className="border-2 border-dashed rounded-md p-8 text-center cursor-pointer hover:bg-muted/50 transition"
            onClick={() => fileRef.current?.click()}
          >
            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm font-medium">
              {file ? file.name : 'Cliquer pour choisir un fichier IFC'}
            </p>
            {file && (
              <p className="text-xs text-muted-foreground mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            )}
            <input
              ref={fileRef}
              type="file"
              accept=".ifc"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Nom du projet</Label>
              <Input value={projectName} onChange={(e) => setProjectName(e.target.value)} />
            </div>
            <div>
              <Label>Auteur</Label>
              <Input value={author} onChange={(e) => setAuthor(e.target.value)} />
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-600 flex items-center gap-2">
              <AlertCircle className="h-4 w-4" /> {error}
            </div>
          )}

          <Button onClick={handleExtract} disabled={loading || !file} className="w-full">
            {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Calculator className="h-4 w-4 mr-2" />}
            Extraire les métrés
          </Button>
        </CardContent>
      </Card>

      {result && result.metres && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Métrés extraits</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-4 gap-3">
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">SB</p>
                <p className="text-xl font-semibold">{result.metres.sb_m2}</p>
                <p className="text-xs text-muted-foreground">m²</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">SRE</p>
                <p className="text-xl font-semibold">{result.metres.sre_m2}</p>
                <p className="text-xs text-muted-foreground">m²</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Volume</p>
                <p className="text-xl font-semibold">{result.metres.volume_m3}</p>
                <p className="text-xs text-muted-foreground">m³</p>
              </div>
              <div className="rounded-md bg-muted/40 p-3">
                <p className="text-xs text-muted-foreground">Espaces</p>
                <p className="text-xl font-semibold">{result.metres.nb_spaces}</p>
                <p className="text-xs text-muted-foreground">IfcSpace</p>
              </div>
            </div>

            <div className="flex gap-2">
              {result.pdf_url && (
                <Button asChild variant="outline">
                  <a href={result.pdf_url} target="_blank" rel="noopener noreferrer" download>
                    <Download className="h-3.5 w-3.5 mr-2" />
                    Rapport PDF
                  </a>
                </Button>
              )}
              {result.dpgf_url && (
                <Button asChild variant="outline">
                  <a href={result.dpgf_url} target="_blank" rel="noopener noreferrer" download>
                    <FileSpreadsheet className="h-3.5 w-3.5 mr-2" />
                    DPGF pré-rempli
                  </a>
                </Button>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              Le chiffreur complétera les prix unitaires dans le DPGF. Les classes IFC
              reconnues sont mappées vers le CFC eCCC-Bât.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

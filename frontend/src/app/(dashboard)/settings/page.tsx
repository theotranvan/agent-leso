'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Download, UserPlus, Trash2 } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { createClient } from '@/lib/supabase';

export default function SettingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<any>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'member' | 'viewer'>('member');
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.me().then(setMe);
  }, []);

  const handleInvite = async () => {
    setInviting(true);
    setInviteMsg(null);
    try {
      await api.inviteUser(inviteEmail, inviteRole);
      setInviteMsg(`Invitation envoyée à ${inviteEmail}`);
      setInviteEmail('');
    } catch (e: any) {
      setInviteMsg(`Erreur : ${e.message}`);
    } finally {
      setInviting(false);
    }
  };

  const handleExport = async () => {
    const data = await api.exportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bet-agent-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDeleteOrg = async () => {
    const confirmed = confirm(
      'Supprimer définitivement l\'organisation et toutes les données associées (projets, documents, tâches) ? Cette action est irréversible.',
    );
    if (!confirmed) return;
    setDeleting(true);
    try {
      await api.deleteAccount();
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push('/login');
    } catch (e: any) {
      alert(`Erreur : ${e.message}`);
      setDeleting(false);
    }
  };

  if (!me) return <div className="text-muted-foreground">Chargement...</div>;

  const isAdmin = me.user?.role === 'admin';

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Paramètres</h1>
        <p className="text-sm text-muted-foreground mt-1">Gérez votre compte et votre organisation</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profil</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-xs text-muted-foreground">Nom</p>
            <p className="text-sm">{me.user?.full_name || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Rôle</p>
            <p className="text-sm capitalize">{me.user?.role}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Organisation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-xs text-muted-foreground">Nom</p>
            <p className="text-sm">{me.organization?.name}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Email</p>
            <p className="text-sm">{me.organization?.email}</p>
          </div>
          {me.organization?.siret && (
            <div>
              <p className="text-xs text-muted-foreground">SIRET</p>
              <p className="text-sm">{me.organization.siret}</p>
            </div>
          )}
          <div>
            <p className="text-xs text-muted-foreground">Plan actuel</p>
            <p className="text-sm capitalize">{me.organization?.plan}</p>
          </div>
        </CardContent>
      </Card>

      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle>Inviter un utilisateur</CardTitle>
            <CardDescription>Ajoutez des collaborateurs à votre organisation</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-[1fr_140px_auto] gap-2">
              <Input
                type="email"
                placeholder="email@exemple.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
              <Select value={inviteRole} onValueChange={(v: any) => setInviteRole(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="member">Membre</SelectItem>
                  <SelectItem value="viewer">Lecteur</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={handleInvite} disabled={inviting || !inviteEmail}>
                <UserPlus className="h-4 w-4 mr-2" />
                Inviter
              </Button>
            </div>
            {inviteMsg && <p className="text-sm text-muted-foreground">{inviteMsg}</p>}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Données personnelles (RGPD)</CardTitle>
          <CardDescription>Exportez ou supprimez l'ensemble des données de votre organisation</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Exporter toutes les données (JSON)
          </Button>
          {isAdmin && (
            <div>
              <Button variant="destructive" onClick={handleDeleteOrg} disabled={deleting}>
                <Trash2 className="h-4 w-4 mr-2" />
                {deleting ? 'Suppression...' : 'Supprimer l\'organisation et toutes les données'}
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                Action irréversible. Tous les projets, documents, tâches et utilisateurs seront supprimés définitivement.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

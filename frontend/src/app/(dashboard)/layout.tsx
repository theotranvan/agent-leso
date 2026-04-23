import { Sidebar } from '@/components/dashboard/sidebar';
import { DashboardHeader } from '@/components/dashboard/header';
import { ActiveProjectProvider } from '@/lib/active-project';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ActiveProjectProvider>
      <div className="flex min-h-screen bg-background">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <DashboardHeader />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-7xl px-6 py-6 md:py-8">{children}</div>
          </main>
        </div>
      </div>
    </ActiveProjectProvider>
  );
}

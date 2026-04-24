import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background-primary text-text-primary p-6">
      <div className="glass-card max-w-md w-full text-center space-y-4">
        <p className="text-xs uppercase tracking-widest text-brand-primary">404</p>
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="text-sm text-text-secondary">
          That page isn&apos;t here. Check the URL or head back to your dashboard.
        </p>
        <div className="pt-2">
          <Link href="/dashboard" className="btn-primary inline-block">
            Go to dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

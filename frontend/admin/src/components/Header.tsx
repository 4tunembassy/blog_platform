import Link from "next/link";

export default function Header() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-slate-900" />
          <div>
            <div className="font-semibold leading-tight">Blog Platform</div>
            <div className="text-xs text-slate-600 leading-tight">
              Admin Console
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-3 text-sm">
          <Link className="hover:underline" href="/">
            Home
          </Link>
          <Link className="hover:underline" href="/content">
            Content
          </Link>
        </nav>
      </div>
    </header>
  );
}

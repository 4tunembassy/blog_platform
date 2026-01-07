export default function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
      {label}
    </div>
  );
}

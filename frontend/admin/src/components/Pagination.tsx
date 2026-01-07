import { clampInt } from "@/lib/utils";

export default function Pagination({
  limit,
  offset,
  total,
  onChange,
}: {
  limit: number;
  offset: number;
  total: number;
  onChange: (nextOffset: number) => void;
}) {
  const prev = clampInt(offset - limit, 0, Math.max(0, total - 1));
  const next = clampInt(offset + limit, 0, Math.max(0, total - 1));

  const canPrev = offset > 0;
  const canNext = offset + limit < total;

  return (
    <div className="flex items-center justify-between gap-3">
      <div className="text-sm text-slate-700">
        Showing{" "}
        <span className="font-medium">{Math.min(total, offset + 1)}</span>–
        <span className="font-medium">{Math.min(total, offset + limit)}</span>{" "}
        of <span className="font-medium">{total}</span>
      </div>

      <div className="flex gap-2">
        <button
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-50"
          onClick={() => onChange(prev)}
          disabled={!canPrev}
        >
          Prev
        </button>
        <button
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 disabled:opacity-50"
          onClick={() => onChange(next)}
          disabled={!canNext}
        >
          Next
        </button>
      </div>
    </div>
  );
}

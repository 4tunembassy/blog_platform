import { clsx } from "@/lib/utils";

export default function Badge({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "slate" | "green" | "amber" | "red" | "blue";
}) {
  const toneCls =
    tone === "green"
      ? "bg-green-50 text-green-700 border-green-200"
      : tone === "amber"
      ? "bg-amber-50 text-amber-800 border-amber-200"
      : tone === "red"
      ? "bg-red-50 text-red-700 border-red-200"
      : tone === "blue"
      ? "bg-blue-50 text-blue-700 border-blue-200"
      : "bg-slate-50 text-slate-700 border-slate-200";

  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs",
        toneCls
      )}
    >
      {children}
    </span>
  );
}

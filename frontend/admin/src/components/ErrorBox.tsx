export default function ErrorBox({
  title = "Error",
  message,
}: {
  title?: string;
  message: string;
}) {
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4">
      <div className="font-semibold text-red-800">{title}</div>
      <div className="mt-1 text-sm text-red-700 whitespace-pre-wrap">
        {message}
      </div>
    </div>
  );
}

export default function Container({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>;
}

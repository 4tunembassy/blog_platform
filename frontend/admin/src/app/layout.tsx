import "./globals.css";
import Header from "@/components/Header";
import Container from "@/components/Container";

export const metadata = {
  title: "Blog Platform Admin",
  description: "Governance-first admin console",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Header />
        <Container>{children}</Container>
      </body>
    </html>
  );
}

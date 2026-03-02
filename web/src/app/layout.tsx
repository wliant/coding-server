import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Multi-Agent Software Development System",
  description: "Submit requirements and let the coding team implement them",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

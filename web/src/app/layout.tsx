import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/nav/Sidebar";
import { ThemeProvider } from "@/components/theme/ThemeProvider";

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
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 p-8">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

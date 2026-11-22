import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Fieldnotes — Research workspace",
  description: "Trace every insight back to its evidence.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sermon Translator",
  description: "Real-time sermon translation for your congregation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

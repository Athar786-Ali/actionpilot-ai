import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ActionPilot AI — Autonomous Web Automation',
  description:
    'Enterprise-grade autonomous browser agent powered by Gemini AI',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

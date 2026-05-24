import "./globals.css";

export const metadata = {
  title: "AI Scientist Workspace",
  description: "Dynamic research workspace for AI Scientist"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

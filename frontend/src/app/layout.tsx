import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adam Setup Agent",
  description: "Adam Setup Agent for DV360 data analysis",
  icons: {
    icon: '/adsecura_logo.png',
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}

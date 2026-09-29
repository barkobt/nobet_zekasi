import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";
import { Providers } from "./providers";

/* DESIGN §3: tek yazı tipi Inter. Monospace yok. */
const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter" });

export const metadata: Metadata = {
  /* Sekme başlığı ve paylaşım kartları. Ürün adı yalnızca "Clinorq";
     kurum adı arayüzde geçmez (ayar olarak tutulur, bkz. app_settings). */
  title: "Clinorq",
  description: "Acil servis nöbet planlama sistemi",
  /* icon.svg ve apple-icon.png app/ altında dosya kuralıyla da bulunur;
     manifest ana ekrana eklemede kullanılır. */
  manifest: "/manifest.webmanifest",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" className={inter.variable}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

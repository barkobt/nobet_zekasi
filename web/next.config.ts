import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Monorepo: kök dizini web/ olarak sabitle. Yoksa Turbopack yukarıdaki
  // klasörlerde lock dosyası arayıp repo dışına çıkıyor.
  turbopack: { root: path.resolve(__dirname) },

  // Geliştirme rozetini sol menünün "Daralt" düğmesinin üstünden kaldır.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;

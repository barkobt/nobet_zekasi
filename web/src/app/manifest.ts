import type { MetadataRoute } from "next";

/**
 * Ana ekrana eklendiğinde görünen kimlik. Renkler DESIGN §2'deki marka
 * token'larıyla aynı hex'ler: burada CSS değişkeni okunamadığı için
 * (manifest tarayıcı öncesi üretilir) değerler elle yazılmak zorunda.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Clinorq",
    short_name: "Clinorq",
    description: "Acil servis nöbet planlama sistemi",
    start_url: "/",
    display: "standalone",
    background_color: "#F5F7FA",
    theme_color: "#0B1F3A",
    icons: [
      {
        src: "/brand/clinorq/app-icon/clinorq-appicon-blue.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}

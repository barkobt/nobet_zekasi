"use client";

import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Tek hata gösterimi (G). Her ekran aynı dili konuşsun: boş ya da kırık ekran
 * yerine tek cümle + "Tekrar dene".
 *
 * Teknik ayrıntı GÖSTERİLMEZ: "fetch failed" bir sorumlu hemşireye hiçbir şey
 * anlatmaz. Sebep ayırt edilebiliyorsa cümle ona göre değişir.
 */
export function HataKutusu({
  hata, onTekrar, kisa,
}: { hata: unknown; onTekrar: () => void; kisa?: boolean }) {
  const metin = (hata as Error)?.message ?? "";
  const mesaj =
    metin.includes("401")
      ? "Oturum doğrulanamadı. Sayfayı yenileyin."
      : metin.includes("404")
      ? "Kayıt bulunamadı."
      : metin.includes("Failed to fetch") || metin.includes("NetworkError")
      ? "Sunucuya ulaşılamıyor."
      : "Veriler alınamadı.";

  return (
    <div
      className={
        "flex flex-col items-center gap-3 rounded-lg border bg-card " +
        (kisa ? "p-6" : "p-12")
      }
    >
      <p className="text-muted-foreground">{mesaj}</p>
      <Button variant="outline" onClick={onTekrar}>
        <RotateCw size={16} strokeWidth={1.75} />
        Tekrar dene
      </Button>
    </div>
  );
}

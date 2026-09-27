"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * Excel indirme. Dosya proxy üzerinden geliyor (token sunucuda kalsın), o yüzden
 * doğrudan <a href> değil fetch + blob: aksi halde tarayıcı Content-Disposition'ı
 * alır ama istek token'sız gider.
 */
export function ExcelDugmesi({
  draftId, dosya = "export.xlsx", etiket = "Excel'e aktar", boyut,
}: {
  draftId: number;
  /** Uç nokta dosya adı: export.xlsx · export-ozet.xlsx · export-eksikler.xlsx */
  dosya?: string;
  etiket?: string;
  boyut?: "sm";
}) {
  const [indiriliyor, setIndiriliyor] = useState(false);

  const indir = async () => {
    setIndiriliyor(true);
    try {
      const yanit = await fetch(`/api/drafts/${draftId}/${dosya}`, { cache: "no-store" });
      if (!yanit.ok) throw new Error(String(yanit.status));

      // Dosya adı sunucudan geliyor (RFC 5987, Türkçe karakterli)
      const bas = yanit.headers.get("content-disposition") ?? "";
      const eslesme = /filename\*=UTF-8''([^;]+)/.exec(bas);
      const ad = eslesme ? decodeURIComponent(eslesme[1]) : "cizelge.xlsx";

      const url = URL.createObjectURL(await yanit.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = ad;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setIndiriliyor(false);
    }
  };

  return (
    <Button variant="outline" size={boyut} onClick={indir} disabled={indiriliyor}>
      {indiriliyor ? (
        <Loader2 size={16} strokeWidth={1.75} className="animate-spin" />
      ) : (
        <Download size={16} strokeWidth={1.75} />
      )}
      {etiket}
    </Button>
  );
}

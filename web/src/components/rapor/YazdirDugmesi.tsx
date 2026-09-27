"use client";

import { Printer } from "lucide-react";

import { Button } from "@/components/ui/button";

/**
 * PDF = tarayıcının yazdırma penceresi. Ayrı bir PDF kütüphanesi yok: aynı
 * hesabı ikinci kez üretmek yerine ekranın kendisini yazdırıyoruz.
 *
 * Hangi bölümün yazdırılacağını <body data-yazdir="..."> söylüyor; globals.css
 * içindeki @media print kuralı diğer her şeyi gizliyor.
 */
export function YazdirDugmesi({ bolum, etiket = "PDF" }: { bolum: string; etiket?: string }) {
  const yazdir = () => {
    document.body.dataset.yazdir = bolum;
    // Yazdırma penceresi kapanınca işareti kaldır; yoksa ekran yarım kalır.
    const temizle = () => {
      delete document.body.dataset.yazdir;
      window.removeEventListener("afterprint", temizle);
    };
    window.addEventListener("afterprint", temizle);
    window.print();
  };

  return (
    <Button variant="outline" size="sm" onClick={yazdir}>
      <Printer size={16} strokeWidth={1.75} />
      {etiket}
    </Button>
  );
}

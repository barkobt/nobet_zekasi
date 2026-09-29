"use client";

import Link from "next/link";

/**
 * Logonun kullanıldığı TEK yer (DESIGN §4.1).
 * Dosyalar docs/brand/clinorq/ altındaki tek doğruluk kaynağından kopyalanır,
 * arayüz yalnızca /brand/clinorq/... okur. Yeniden çizilmez, renk/oran
 * değiştirilmez, yerine başka logo konmaz.
 *
 * Sol menü koyu zemin → `-reverse` varyantları kullanılır.
 * Menü açıkken yatay kilit (işaret + "clinorq"), kapalıyken yalnız işaret.
 * İki dosya üst üste durur ve opacity ile geçer; işaret ikisinde de sola
 * dayalı ve aynı yükseklikte olduğu için geçişte yerinden oynamaz.
 *
 * NEDEN iki ayrı dosya: wordmark dosyasındaki "q" harfi zaten işaretin
 * kendisidir. İşaret + wordmark'ı yan yana koymak "q"yu iki kez gösterirdi.
 */

/* Yatay kilidin içindeki işaret, tek başına duran işaretten oransal olarak
   biraz daha küçük çiziliyor (dosyaların kendi boşlukları farklı). 24 → 23 px
   düzeltmesi ikisini aynı optik boyuta getirir. */
const YATAY_YUKSEKLIK = 24;
const ISARET_YUKSEKLIK = 23;

export function BrandLogo({ collapsed }: { collapsed: boolean }) {
  return (
    <Link
      href="/"
      aria-label="Clinorq — Ana Sayfa"
      title={collapsed ? "Clinorq" : undefined}
      className="flex h-14 shrink-0 items-center overflow-hidden px-4"
    >
      <span className="relative flex h-6 items-center" aria-hidden>
        <img
          src="/brand/clinorq/symbol/clinorq-symbol-reverse.svg"
          alt=""
          height={ISARET_YUKSEKLIK}
          className="shrink-0 transition-opacity duration-150 ease-out motion-reduce:transition-none"
          style={{ height: ISARET_YUKSEKLIK, opacity: collapsed ? 1 : 0 }}
        />
        <img
          src="/brand/clinorq/horizontal/clinorq-horizontal-reverse.svg"
          alt=""
          height={YATAY_YUKSEKLIK}
          className="absolute left-0 max-w-none shrink-0 transition-opacity duration-150 ease-out motion-reduce:transition-none"
          style={{ height: YATAY_YUKSEKLIK, opacity: collapsed ? 0 : 1 }}
        />
      </span>
    </Link>
  );
}

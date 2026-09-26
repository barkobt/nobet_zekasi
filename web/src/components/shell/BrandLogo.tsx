"use client";

import Link from "next/link";

/**
 * Logonun kullanıldığı TEK yer (DESIGN §4.1).
 * Dosyalar docs/brand/ altındaki tek doğruluk kaynağından kopyalanır, /brand/... okunur.
 * Yeniden çizilmez, renk/oran değiştirilmez, yerine başka logo konmaz.
 *
 * Menü açıkken ACIBADEM yazısı, kapalıyken yalnız Λ işareti. Geçiş 150ms opacity;
 * hover artık menünün kendisini açtığı için logonun ayrı bir hover davranışı yok.
 */
export function BrandLogo({ collapsed }: { collapsed: boolean }) {
  return (
    <Link
      href="/"
      aria-label="Acıbadem Smart Planner — Ana Sayfa"
      title={collapsed ? "Acıbadem Smart Planner" : undefined}
      className="flex h-14 shrink-0 items-center gap-3 overflow-hidden px-4"
    >
      <img
        src="/brand/acibadem-mark.svg"
        alt=""
        width={24}
        height={24}
        className="h-6 w-6 shrink-0"
      />
      <img
        src="/brand/acibadem-wordmark.svg"
        alt="ACIBADEM"
        className="h-[13px] w-auto shrink-0 transition-opacity duration-150 ease-out"
        style={{ opacity: collapsed ? 0 : 1 }}
      />
    </Link>
  );
}

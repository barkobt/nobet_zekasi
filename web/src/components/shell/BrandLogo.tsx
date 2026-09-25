"use client";

import Link from "next/link";

/**
 * Logonun kullanıldığı TEK yer (DESIGN §4.1).
 * Dosyalar docs/brand/ altındaki tek doğruluk kaynağından kopyalanır, /brand/... okunur.
 * Yeniden çizilmez, renk/oran değiştirilmez, yerine başka logo konmaz.
 *
 * Geçiş: iki katman üst üste (absolute), yalnız opacity + 4px translateX, 200ms ease-out.
 * Genişlik sabit kalır → hover'da layout kaymaz.
 */
export function BrandLogo({ collapsed }: { collapsed: boolean }) {
  return (
    <Link
      href="/cizelge"
      aria-label="Acıbadem Smart Planner — Nöbet Çizelgesi"
      title={collapsed ? "Acıbadem Smart Planner" : undefined}
      className="group flex h-14 shrink-0 items-center gap-2 px-4 rounded-md"
    >
      {/* İşaret her durumda görünür; yalnızca menü genişken hover'da solar. */}
      <img
        src="/brand/acibadem-mark.svg"
        alt=""
        width={24}
        height={24}
        className={
          "h-6 w-6 shrink-0 transition-opacity duration-200 ease-out " +
          (collapsed ? "" : "group-hover:opacity-0 group-focus-visible:opacity-0")
        }
      />

      {collapsed ? null : (
        // Sabit genişlikli kap: iki katman da içinde, biri solup diğeri belirir.
        <span className="relative h-4 w-[132px]">
          <span
            className="absolute inset-0 flex items-center text-white opacity-100 transition-all duration-200 ease-out
                       group-hover:-translate-x-1 group-hover:opacity-0
                       group-focus-visible:-translate-x-1 group-focus-visible:opacity-0"
            style={{ fontSize: "var(--text-base)", fontWeight: 600 }}
          >
            Smart Planner
          </span>
          <img
            src="/brand/acibadem-wordmark.svg"
            alt="ACIBADEM"
            className="absolute inset-0 h-4 w-auto translate-x-1 opacity-0 transition-all duration-200 ease-out
                       group-hover:translate-x-0 group-hover:opacity-100
                       group-focus-visible:translate-x-0 group-focus-visible:opacity-100"
          />
        </span>
      )}
    </Link>
  );
}

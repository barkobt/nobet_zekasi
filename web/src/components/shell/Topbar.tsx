"use client";

import { usePathname } from "next/navigation";
import { NAV } from "@/lib/navigation";

/**
 * DESIGN §4: 56px, --surface zemin, alt çizgi. Sol menünün SAĞINDAN başlar —
 * lacivert sütun kesintisiz yukarı çıksın diye logo üst barda değil.
 * Solda birim adı, sağda dönem gezgini.
 */
export function Topbar({ period }: { period?: React.ReactNode }) {
  const pathname = usePathname();
  const sayfa = NAV.find((n) => (n.href === "/" ? pathname === "/" : pathname.startsWith(n.href)));

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-card px-6">
      <div className="flex items-baseline gap-3">
        <span style={{ fontSize: "var(--text-base)", fontWeight: 600 }}>
          {sayfa?.label ?? "Acıbadem Smart Planner"}
        </span>
        <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
          Erişkin Acil Servis
        </span>
      </div>
      {period}
    </header>
  );
}

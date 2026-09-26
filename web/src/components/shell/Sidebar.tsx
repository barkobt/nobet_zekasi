"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Pin, PinOff } from "lucide-react";

import { BrandLogo } from "./BrandLogo";
import { NAV_GROUPS } from "@/lib/navigation";

const DAR = 64;
const GENIS = 224;

/**
 * DESIGN §4: varsayılan DARALTILMIŞ (64px). Fare üzerine gelince genişler ama
 * içeriği İTMEZ — üstüne biner. Sabitlenirse (pin) açık kalır ve iter.
 *
 * Genişleme iki katmanla yapılıyor: dıştaki şerit her zaman sabit genişlikte
 * (yer tutar), içteki panel absolute olarak onun üstünde büyür. Böylece hover'da
 * sayfa içeriği kaymıyor.
 */
export function Sidebar({
  acik, sabit, onHover, onSabit,
}: {
  acik: boolean;
  sabit: boolean;
  onHover: (v: boolean) => void;
  onSabit: () => void;
}) {
  const pathname = usePathname();

  return (
    <div
      className="relative h-dvh shrink-0 transition-[width] duration-150 ease-out"
      style={{ width: sabit ? GENIS : DAR }}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
    >
      <nav
        aria-label="Ana menü"
        className="absolute inset-y-0 left-0 z-40 flex flex-col overflow-hidden bg-brand text-white transition-[width] duration-150 ease-out"
        style={{ width: acik ? GENIS : DAR }}
      >
        <BrandLogo collapsed={!acik} />

        <div className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-1">
          {NAV_GROUPS.map((grup) => (
            <div key={grup.ad} className="mb-1">
              {/* Grup başlığı yalnız açıkken; kapalıyken ince bir ayraç */}
              {acik ? (
                <div
                  className="px-3 pb-1 pt-2 text-white/45"
                  style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
                >
                  {grup.ad.toUpperCase()}
                </div>
              ) : (
                <div className="mx-2 my-2 border-t border-white/15" aria-hidden />
              )}

              <ul>
                {grup.items.map((item) => {
                  // "/" her yolun ön eki: ana sayfa yalnız tam eşleşmede aktif
                  const aktif =
                    item.href === "/"
                      ? pathname === "/"
                      : pathname === item.href || pathname.startsWith(item.href + "/");
                  const Icon = item.icon;

                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        aria-current={aktif ? "page" : undefined}
                        title={acik ? undefined : item.label}
                        className={
                          "relative flex h-10 items-center gap-3 rounded-md px-3 transition-colors duration-150 " +
                          (aktif
                            ? "bg-brand-hover text-white"
                            : "text-white/70 hover:bg-brand-hover hover:text-white")
                        }
                      >
                        {/* Aktiflik yalnız renkle verilmiyor: sol çizgi de var (DESIGN §8) */}
                        {aktif && (
                          <span
                            aria-hidden
                            className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r bg-focus"
                          />
                        )}
                        <Icon size={20} strokeWidth={1.75} className="shrink-0" />
                        <span
                          className="truncate transition-opacity duration-150"
                          style={{ opacity: acik ? 1 : 0 }}
                        >
                          {item.label}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Sabitleme: yalnız menü açıkken görünür, küçük ve sessiz */}
        <button
          type="button"
          onClick={onSabit}
          aria-label={sabit ? "Menüyü serbest bırak" : "Menüyü sabitle"}
          aria-pressed={sabit}
          className="m-2 flex h-9 items-center gap-2 rounded-md px-3 text-white/55 transition-opacity duration-150 hover:bg-brand-hover hover:text-white"
          style={{ opacity: acik ? 1 : 0, pointerEvents: acik ? "auto" : "none" }}
        >
          {sabit ? <PinOff size={16} strokeWidth={1.75} /> : <Pin size={16} strokeWidth={1.75} />}
          <span style={{ fontSize: "var(--text-xs)" }}>{sabit ? "Serbest" : "Sabitle"}</span>
        </button>
      </nav>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { BrandLogo } from "./BrandLogo";
import { NAV } from "@/lib/navigation";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

/**
 * DESIGN §4: lacivert, tam yükseklik. Genişken 224px, daraltılınca 64px (yalnız ikon).
 * Aktif öğe: beyaz metin + sol 3px --accent çizgi.
 */
export function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Ana menü"
      className="flex h-dvh shrink-0 flex-col bg-brand text-white transition-[width] duration-200 ease-out"
      style={{ width: collapsed ? 64 : 224 }}
    >
      <BrandLogo collapsed={collapsed} />

      <ul className="flex flex-1 flex-col gap-0.5 px-2 py-2">
        {NAV.map((item) => {
          const aktif = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;

          const link = (
            <Link
              href={item.href}
              aria-current={aktif ? "page" : undefined}
              className={
                "relative flex h-10 items-center gap-3 rounded-md px-3 transition-colors duration-150 " +
                (aktif
                  ? "bg-brand-hover text-white"
                  : "text-white/70 hover:bg-brand-hover hover:text-white")
              }
            >
              {/* Aktif göstergesi yalnızca renkle verilmiyor: sol çizgi de var (DESIGN §8). */}
              {aktif && (
                <span
                  aria-hidden
                  className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r bg-focus"
                />
              )}
              <Icon size={20} strokeWidth={1.75} className="shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );

          return (
            <li key={item.href}>
              {collapsed ? (
                <Tooltip>
                  <TooltipTrigger asChild>{link}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              ) : (
                link
              )}
            </li>
          );
        })}
      </ul>

      <button
        type="button"
        onClick={onToggle}
        aria-label={collapsed ? "Menüyü genişlet" : "Menüyü daralt"}
        className="m-2 flex h-10 items-center gap-3 rounded-md px-3 text-white/70 transition-colors duration-150 hover:bg-brand-hover hover:text-white"
      >
        {collapsed ? (
          <PanelLeftOpen size={20} strokeWidth={1.75} />
        ) : (
          <PanelLeftClose size={20} strokeWidth={1.75} />
        )}
        {!collapsed && <span>Daralt</span>}
      </button>
    </nav>
  );
}

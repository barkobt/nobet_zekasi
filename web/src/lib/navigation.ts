import {
  Home, CalendarDays, Layers, ClipboardList,
  Users, Grid3x3, Scale, Clock,
  type LucideIcon,
} from "lucide-react";

export type NavItem = { href: string; label: string; kod: string; icon: LucideIcon };
export type NavGroup = { ad: string; items: NavItem[] };

/** Sol menü (DESIGN §4): üç grup, ince başlıklarla. Dashboard yok, E-00 var. */
export const NAV_GROUPS: NavGroup[] = [
  {
    ad: "Planlama",
    items: [
      { href: "/",          label: "Ana Sayfa",       kod: "E-00", icon: Home },
      { href: "/cizelge",   label: "Nöbet Çizelgesi", kod: "E-09", icon: CalendarDays },
      { href: "/taslaklar", label: "Taslaklar",       kod: "E-08", icon: Layers },
      { href: "/ihtiyac",   label: "İhtiyaç",         kod: "E-06", icon: ClipboardList },
    ],
  },
  {
    ad: "Kadro",
    items: [
      { href: "/personel",  label: "Personel",          kod: "E-04", icon: Users },
      { href: "/yetkinlik", label: "Yetkinlik Matrisi", kod: "E-02", icon: Grid3x3 },
    ],
  },
  {
    ad: "Ayarlar",
    items: [
      { href: "/kurallar",   label: "Kural Seti",        kod: "E-03", icon: Scale },
      { href: "/vardiyalar", label: "Vardiya Tanımları", kod: "E-01", icon: Clock },
    ],
  },
];

export const NAV: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

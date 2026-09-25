import {
  CalendarDays, Layers, Stethoscope, Users, Grid3x3, Scale, ClipboardList, Clock,
  type LucideIcon,
} from "lucide-react";

/** Sol menü = DESIGN §6'daki MVP ekranları, aynı sırada. Dashboard MVP'de yok. */
export type NavItem = { href: string; label: string; kod: string; icon: LucideIcon };

export const NAV: NavItem[] = [
  { href: "/cizelge",    label: "Nöbet Çizelgesi",   kod: "E-09", icon: CalendarDays },
  { href: "/taslaklar",  label: "Taslaklar",         kod: "E-08", icon: Layers },
  { href: "/teshis",     label: "Çözüm Teşhisi",     kod: "E-10", icon: Stethoscope },
  { href: "/personel",   label: "Personel",          kod: "E-04", icon: Users },
  { href: "/yetkinlik",  label: "Yetkinlik Matrisi", kod: "E-02", icon: Grid3x3 },
  { href: "/kurallar",   label: "Kural Seti",        kod: "E-03", icon: Scale },
  { href: "/ihtiyac",    label: "İhtiyaç Şablonu",   kod: "E-06", icon: ClipboardList },
  { href: "/vardiyalar", label: "Vardiya Tanımları", kod: "E-01", icon: Clock },
];

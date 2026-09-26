"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

import { GunBasligi } from "./GunBasligi";
import { Hucre } from "./Hucre";
import { fark, sayi, type Schedule } from "@/lib/cizelge";
import { HucreDuzenle } from "./HucreDuzenle";

/**
 * E-09 ızgarası (DESIGN §6):
 *   satır = personel, rol grubuna göre katlanabilir bölümler
 *   sütun = gün, başlıkta G x/y ve N x/y
 *   satır sonu = aylık toplam + 200 hedefine göre fark
 * İlk sütun ve başlık satırı sabit (sticky).
 */
export function Izgara({
  data, draftId, onDegisti,
}: {
  data: Schedule;
  /** Verilirse hücreler düzenlenebilir olur (taslak içi ekran). */
  draftId?: number;
  onDegisti?: () => void;
}) {
  // Hedef artık döneme orantılı (aylık hedef × gün sayısı / ayın gün sayısı), ama
  // KIRMIZI yalnızca taslak ayın tamamını kapsıyorsa: C-004 aylık bir kuraldır,
  // bir haftalık çizelgede "hedefin altında" demek kuralın ihlali değildir.
  const ayTam = data.draft.covers_full_month;
  const [kapali, setKapali] = useState<Set<string>>(new Set());

  const degistir = (k: string) =>
    setKapali((v) => {
      const y = new Set(v);
      y.has(k) ? y.delete(k) : y.add(k);
      return y;
    });

  return (
    <div className="overflow-auto rounded-lg border bg-card">
      <table className="w-full border-collapse" style={{ fontSize: "var(--text-base)" }}>
        <thead>
          <tr>
            <th className="sticky left-0 top-0 z-30 min-w-[200px] border-b border-r bg-card p-0 text-left align-bottom">
              <span
                className="block px-3 pb-2 text-muted-foreground"
                style={{ fontSize: "var(--text-xs)" }}
              >
                Personel
              </span>
            </th>
            {data.days.map((g) => (
              <th
                key={g.day}
                className={
                  "sticky top-0 z-20 min-w-[92px] border-b bg-card p-0 " +
                  (g.is_weekend ? "bg-background" : "")
                }
              >
                <GunBasligi gun={g} />
              </th>
            ))}
            <th className="sticky right-0 top-0 z-30 min-w-[110px] border-b border-l bg-card p-0 align-bottom">
              <span
                className="block px-3 pb-2 text-right text-muted-foreground"
                style={{ fontSize: "var(--text-xs)" }}
              >
                Dönem toplamı
              </span>
            </th>
          </tr>
        </thead>

        {data.groups.map((grup) => {
          const acik = !kapali.has(grup.key);
          return (
            <tbody key={grup.key}>
              <tr>
                <th
                  colSpan={data.days.length + 2}
                  className="sticky left-0 z-10 border-b bg-background p-0 text-left"
                >
                  <button
                    type="button"
                    onClick={() => degistir(grup.key)}
                    aria-expanded={acik}
                    className="flex h-9 w-full items-center gap-1.5 px-3 text-muted-foreground hover:text-foreground"
                    style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
                  >
                    {acik ? (
                      <ChevronDown size={16} strokeWidth={1.75} />
                    ) : (
                      <ChevronRight size={16} strokeWidth={1.75} />
                    )}
                    <span className="uppercase">{grup.label}</span>
                    <span className="normal-case">({grup.rows.length})</span>
                  </button>
                </th>
              </tr>

              {acik &&
                grup.rows.map((satir) => (
                  <tr key={satir.staff_id} className="group border-b last:border-0">
                    <th className="sticky left-0 z-10 border-r bg-card p-0 text-left font-normal group-hover:bg-accent">
                      <div className="flex h-10 items-center gap-2 px-3">
                        <span
                          className="flex size-6 shrink-0 items-center justify-center rounded-sm bg-secondary text-secondary-foreground"
                          style={{ fontSize: "var(--text-xs)" }}
                          aria-hidden
                        >
                          {satir.initials}
                        </span>
                        <span className="truncate font-medium">{satir.full_name}</span>
                        {satir.is_orientation && (
                          <span
                            className="shrink-0 text-muted-foreground"
                            style={{ fontSize: "var(--text-xs)" }}
                            title="Oryantasyon"
                          >
                            ory.
                          </span>
                        )}
                      </div>
                    </th>

                    {data.days.map((g) => (
                      <td
                        key={g.day}
                        className={
                          "h-10 border-l p-0 align-middle group-hover:bg-accent " +
                          (g.is_weekend ? "bg-background/60" : "")
                        }
                      >
                        {draftId ? (
                          <HucreDuzenle
                            draftId={draftId}
                            staffId={satir.staff_id}
                            staffName={satir.full_name}
                            gun={g.day}
                            cell={satir.cells[g.day] ?? undefined}
                            absence={(satir.absences ?? {})[g.day] ?? undefined}
                            onKaydedildi={() => onDegisti?.()}
                          >
                            <button
                              type="button"
                              className="h-full w-full cursor-pointer hover:bg-brand-soft"
                              aria-label={`${satir.full_name} — ${g.label}`}
                            >
                              <Hucre
                                cell={satir.cells[g.day] ?? undefined}
                                absence={(satir.absences ?? {})[g.day] ?? undefined}
                              />
                            </button>
                          </HucreDuzenle>
                        ) : (
                          <Hucre
                            cell={satir.cells[g.day] ?? undefined}
                            absence={(satir.absences ?? {})[g.day] ?? undefined}
                          />
                        )}
                      </td>
                    ))}

                    <td className="sticky right-0 z-10 border-l bg-card px-3 text-right group-hover:bg-accent">
                      <div className="flex flex-col leading-tight">
                        <span className="font-medium">{sayi(satir.period_hours)} sa</span>
                        <span
                          className={
                            ayTam && satir.period_diff < 0
                              ? "text-danger font-medium"
                              : "text-muted-foreground"
                          }
                          style={{ fontSize: "var(--text-xs)" }}
                        >
                          {fark(satir.period_diff)}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          );
        })}
      </table>
    </div>
  );
}

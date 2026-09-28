"use client";

import { useState } from "react";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";

import { GunBasligi } from "./GunBasligi";
import { Hucre } from "./Hucre";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { SatirOzeti } from "./SatirOzeti";
import { useOzetPaneli } from "./DetayDugmesi";
import { sayi, type Schedule } from "@/lib/cizelge";
import { HucreDuzenle } from "./HucreDuzenle";

/**
 * E-09 ızgarası (DESIGN §6):
 *   satır = personel, rol grubuna göre katlanabilir bölümler
 *   sütun = gün, başlıkta G x/y ve N x/y
 *   satır sonu = aylık toplam + 200 hedefine göre fark
 * İlk sütun ve başlık satırı sabit (sticky).
 */
/**
 * Dönem dışı gün: çapraz taralı ve soluk. İçerik YAYINLANMIŞ çizelgeden gelir ve
 * düzenlenemez — komşu ayın nöbetini buradan değiştirmek, yayınlanmış bir çizelgeyi
 * kimsenin haberi olmadan değiştirmek olurdu.
 */
const DONEM_DISI: React.CSSProperties = {
  backgroundImage:
    "repeating-linear-gradient(45deg, var(--border) 0 1px, transparent 1px 7px)",
};

export function Izgara({
  data, draftId, onDegisti, detaylar = false,
}: {
  data: Schedule;
  /** Verilirse hücreler düzenlenebilir olur (taslak içi ekran). */
  draftId?: number;
  onDegisti?: () => void;
  /** "Detayları göster" açık mı: ek sayaçlar + hücrede saat etiketi. */
  detaylar?: boolean;
}) {
  // Aylık görünümde gün sayısı 28-31: hücreler daralır, yalnız G/N harfi kalır.
  const aylik = data.view === "monthly";
  const sayaclar = data.counters ?? [];
  const gorunenSayac = sayaclar.filter((c) => c.visible);

  // Özet paneli: ok tüm satırlar için açar/kapar (tercih veritabanında).
  // Kişinin ADINA tıklamak YALNIZ o satırı ters çevirir — panel kapalıyken de
  // tek bir kişinin özetine bakılabilsin.
  const { acik: panelAcik, cevir: paneliCevir } = useOzetPaneli();
  const [ters, setTers] = useState<Set<number>>(new Set());
  const ozetAcik = (id: number) => (ters.has(id) ? !panelAcik : panelAcik);
  const kisiyiCevir = (id: number) =>
    setTers((v) => {
      const y = new Set(v);
      if (y.has(id)) y.delete(id);
      else y.add(id);
      return y;
    });

  // Panel açıkken sayaç kutuları TEK SATIRDA sığmalı: kutu 38px + 4px boşluk,
  // iki yandan 8'er px iç boşluk. Alt satıra taşarlarsa satır yüksekliği
  // kişiden kişiye değişiyor ve ızgara dalgalanıyor.
  // Panel kapalı olsa bile TEK BİR kişinin özeti açıksa sütun o kutuları
  // taşıyacak kadar geniş olmalı; yoksa bildirilen genişlik ile içerik çelişir
  // ve sütun kendiliğinden büyüyüp başlıkla hizasız kalır.
  const ozetVar = panelAcik || ters.size > 0;
  const ozetGenislik = ozetVar ? gorunenSayac.length * 42 + 18 : 34;

  // Aylık görünümde 31 sütun yan yana: haftaların nerede bittiği ancak bir ayraçla
  // okunur. Pazartesi sütununun soluna daha belirgin bir çizgi konur.
  const haftaBasi = (iso: string) =>
    aylik && new Date(iso + "T00:00:00Z").getUTCDay() === 1;
  const ayrac = "border-l-2 border-l-border";
  // Hedef saat orantılanmaz (27.09): tam ay → 200 (C-004), tam hafta → 50 (C-003),
  // başka uzunlukta hedef yok ve fark sütunu "—" gösterir. Kırmızı yalnız hedef
  // varken ve altında kalınmışken.
  const [kapali, setKapali] = useState<Set<string>>(new Set());

  const degistir = (k: string) =>
    setKapali((v) => {
      const y = new Set(v);
      y.has(k) ? y.delete(k) : y.add(k);
      return y;
    });

  return (
    <div className="izgara-kaydirma overflow-auto rounded-lg border bg-card">
      <table className="w-full border-collapse" style={{ fontSize: "var(--text-base)" }}>
        <thead>
          <tr>
            {/* Özet paneli — personel sütununun SOLUNDA, daraltılabilir */}
            <th
              className="sticky left-0 top-0 z-30 border-b border-r bg-card p-0 align-bottom"
              style={{ width: ozetGenislik, minWidth: ozetGenislik }}
            >
              {/* Ok yuvarlak gri bir kutuda: çıplak ikon hem küçük kalıyor hem
                  tıklanabilir olduğu anlaşılmıyordu. Kapalıyken yalnız kutu,
                  açıkken yanında "Özet" yazısı. */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={paneliCevir}
                    aria-expanded={panelAcik}
                    aria-label={panelAcik ? "Özet panelini daralt" : "Özet panelini genişlet"}
                    className="flex h-full w-full items-center justify-center gap-1.5 px-2 pb-2 pt-2"
                  >
                    <span
                      className="flex size-6 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground"
                      style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
                    >
                      {panelAcik
                        ? <ChevronLeft size={14} strokeWidth={2} />
                        : <ChevronRight size={14} strokeWidth={2} />}
                    </span>
                    {panelAcik && (
                      <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
                        Özet
                      </span>
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  {panelAcik
                    ? "Özet panelini daralt"
                    : "Özet panelini aç — kişi başına sayaçlar"}
                </TooltipContent>
              </Tooltip>
            </th>

            <th
              className="sticky top-0 z-30 min-w-[210px] border-b border-r bg-card p-0 text-left align-bottom"
              style={{ left: ozetGenislik }}
            >
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
                  "sticky top-0 z-20 border-b bg-card p-0 " +
                  (aylik ? "min-w-[38px] " : "min-w-[92px] ") +
                  (g.is_weekend ? "bg-background " : "") +
                  (g.in_period === false ? "opacity-55 " : "") +
                  (haftaBasi(g.day) ? ayrac + " " : "")
                }
                style={g.in_period === false ? DONEM_DISI : undefined}
              >
                <GunBasligi gun={g} dar={aylik} />
              </th>
            ))}
          </tr>
        </thead>

        {data.groups.map((grup) => {
          const acik = !kapali.has(grup.key);
          return (
            <tbody key={grup.key}>
              <tr>
                <th
                  colSpan={data.days.length + 2}
                  className="z-10 border-b bg-background p-0 text-left"
                >
                  {/* Etiket hücrenin İÇİNDE sabit: hücre tablo kadar geniş olduğu
                      için sticky'yi hücreye vermek yetmiyor, yatay kaydırınca
                      başlık sola kayıp gidiyordu. */}
                  <button
                    type="button"
                    onClick={() => degistir(grup.key)}
                    aria-expanded={acik}
                    className="sticky left-0 flex h-9 items-center gap-1.5 px-3 text-muted-foreground hover:text-foreground"
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
                    {/* Sol özet hücresi: sayaç kutuları ya da boş */}
                    <td
                      className="sticky left-0 z-10 border-r bg-card p-0 align-middle group-hover:bg-accent"
                      style={{ width: ozetGenislik, minWidth: ozetGenislik }}
                    >
                      {ozetAcik(satir.staff_id) && (
                        <SatirOzeti satir={satir} sayaclar={sayaclar} />
                      )}
                    </td>

                    <th
                      className="sticky z-10 border-r bg-card p-0 text-left font-normal group-hover:bg-accent"
                      style={{ left: ozetGenislik }}
                    >
                      <div className="flex h-10 items-center gap-2 px-3">
                        <span
                          className="flex size-6 shrink-0 items-center justify-center rounded-sm bg-secondary text-secondary-foreground"
                          style={{ fontSize: "var(--text-xs)" }}
                          aria-hidden
                        >
                          {satir.initials}
                        </span>
                        {/* Ada tıklamak YALNIZ bu satırın özetini açar/kapatır */}
                        <button
                          type="button"
                          onClick={() => kisiyiCevir(satir.staff_id)}
                          aria-expanded={ozetAcik(satir.staff_id)}
                          aria-label={`${satir.full_name} özetini aç/kapat`}
                          className="truncate font-medium hover:underline"
                        >
                          {satir.full_name}
                        </button>
                        {satir.period_target != null && (
                          <span
                            className="shrink-0 rounded-sm px-1.5 py-0.5 tabular-nums"
                            style={{
                              background: "var(--brand-soft)",
                              color: "var(--brand)",
                              fontSize: "var(--text-xs)",
                            }}
                            title="Dönem hedefi"
                          >
                            {sayi(satir.period_target)}s
                          </span>
                        )}
                        {!satir.is_active && (
                          <span
                            className="shrink-0 text-muted-foreground"
                            style={{ fontSize: "var(--text-xs)" }}
                            title="Ayrıldı — kapsamaya sayılır, adalet hesabına girmez"
                          >
                            ayrıldı
                          </span>
                        )}
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

                    {data.days.map((g) => {
                      const hucre = satir.cells[g.day] ?? undefined;
                      const izin = (satir.absences ?? {})[g.day] ?? undefined;
                      const istek = (satir.requests ?? {})[g.day] ?? undefined;
                      // Dönem dışı gün ASLA düzenlenmez; hücre yoksa da düzenlenemez
                      // (o günün sahibi başka bir çizelge).
                      const duzenlenir =
                        draftId !== undefined && g.in_period !== false;
                      return (
                      <td
                        key={g.day}
                        className={
                          "h-10 border-l p-0 align-middle group-hover:bg-accent " +
                          (g.is_weekend ? "bg-background " : "") +
                          (g.in_period === false ? "opacity-55 " : "") +
                          (haftaBasi(g.day) ? ayrac + " " : "")
                        }
                        style={g.in_period === false ? DONEM_DISI : undefined}
                      >
                        {duzenlenir ? (
                          <HucreDuzenle
                            draftId={draftId!}
                            staffId={satir.staff_id}
                            staffName={satir.full_name}
                            gun={g.day}
                            cell={hucre}
                            absence={izin}
                            onKaydedildi={() => onDegisti?.()}
                          >
                            <button
                              type="button"
                              className="h-full w-full cursor-pointer hover:bg-brand-soft"
                              aria-label={`${satir.full_name} — ${g.label}`}
                            >
                              <Hucre
                                cell={hucre}
                                absence={izin}
                                request={istek}
                                saatGoster={detaylar && !aylik}
                                dar={aylik}
                              />
                            </button>
                          </HucreDuzenle>
                        ) : (
                          <Hucre
                            cell={hucre}
                            absence={izin}
                            request={istek}
                            saatGoster={detaylar && !aylik}
                            dar={aylik}
                          />
                        )}
                      </td>
                      );
                    })}

                  </tr>
                ))}
            </tbody>
          );
        })}
      </table>
    </div>
  );
}

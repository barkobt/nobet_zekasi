"use client";

import { Fragment, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Plus, Search } from "lucide-react";

import { AppShell } from "@/components/shell/AppShell";
import { DetayPaneli } from "@/components/personel/DetayPaneli";
import { HataKutusu } from "@/components/HataKutusu";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { CALISMA_TIPI, basHarf, type PersonDetail, type PersonRow, type Role } from "@/lib/personel";

/** Sıralanabilir sütunlar. */
type Alan = "sicil" | "ad" | "soyad" | "rol" | "grup" | "tip" | "hedef";

function Baslik({
  alan, genislik, sag, sirala, onSirala, children,
}: {
  alan: Alan;
  genislik?: string;
  sag?: boolean;
  sirala: { alan: Alan; yon: "artan" | "azalan" } | null;
  onSirala: (a: Alan) => void;
  children: React.ReactNode;
}) {
  const etkin = sirala?.alan === alan;
  return (
    <TableHead style={genislik ? { width: genislik } : undefined} className={sag ? "text-right" : ""}>
      <button
        type="button"
        onClick={() => onSirala(alan)}
        className="inline-flex items-center gap-1 hover:text-foreground"
        aria-label={`${String(children)} sütununa göre sırala`}
      >
        {children}
        {etkin &&
          (sirala.yon === "artan"
            ? <ArrowUp size={12} strokeWidth={2} aria-hidden />
            : <ArrowDown size={12} strokeWidth={2} aria-hidden />)}
      </button>
    </TableHead>
  );
}

export default function PersonelSayfasi() {
  const [arama, setArama] = useState("");
  const [rolFiltre, setRolFiltre] = useState("");
  const [tipFiltre, setTipFiltre] = useState("");
  const [secili, setSecili] = useState<number | null>(null);
  // Bir satır seçilince ekran ikiye bölünür: solda daralmış liste, sağda detay.
  const bolunmus = secili !== null;

  const [durum, setDurum] = useState<"aktif" | "pasif" | "hepsi">("aktif");
  const [sirala, setSirala] = useState<{ alan: Alan; yon: "artan" | "azalan" } | null>(null);

  const sirayaAl = (alan: Alan) =>
    setSirala((e) =>
      e?.alan === alan
        ? { alan, yon: e.yon === "artan" ? "azalan" : "artan" }
        : { alan, yon: "artan" },
    );

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["people", durum],
    queryFn: () => api<PersonRow[]>(`/people?durum=${durum}`),
  });

  // Arama ve filtreler istemcide: 20 kişi, sunucuya gitmeye değmez.
  const satirlar = useMemo(() => {
    const q = arama.trim().toLocaleLowerCase("tr");
    return (data ?? []).filter(
      (p) =>
        (!q || p.full_name.toLocaleLowerCase("tr").includes(q)
            || (p.sicil_no ?? "").toLocaleLowerCase("tr").includes(q)) &&
        (!rolFiltre || p.role_code === rolFiltre) &&
        (!tipFiltre || p.shift_eligibility === tipFiltre),
    );
  }, [data, arama, rolFiltre, tipFiltre]);

  // Sütun sıralaması: aynı sütuna ikinci tıklayış yönü çevirir.
  const siralilar = useMemo(() => {
    if (!sirala) return satirlar;
    const { alan, yon } = sirala;
    const anahtar = (p: PersonRow): string | number =>
      alan === "sicil" ? (p.sicil_no ?? "")
      : alan === "ad" ? p.first_name
      : alan === "soyad" ? p.last_name
      : alan === "rol" ? p.role_name
      : alan === "grup" ? p.display_group
      : alan === "tip" ? p.eligibility_label
      : (p.monthly_target_hours ?? 0);
    return [...satirlar].sort((a, b) => {
      const x = anahtar(a), y = anahtar(b);
      const k = typeof x === "number" && typeof y === "number"
        ? x - y
        : String(x).localeCompare(String(y), "tr");
      return yon === "artan" ? k : -k;
    });
  }, [satirlar, sirala]);

  // Gruplar ARTIK VERİTABANINDAN (roles.display_group / sort_order). Sabit dizi
  // kalkınca yeni bir rol eklendiğinde listede kaybolmuyor.
  const gruplar = useMemo(() => {
    const m = new Map<string, { ad: string; sira: number; satirlar: PersonRow[] }>();
    for (const p of siralilar) {
      const g = m.get(p.display_group) ?? {
        ad: p.display_group, sira: p.group_order, satirlar: [],
      };
      g.sira = Math.min(g.sira, p.group_order);
      g.satirlar.push(p);
      m.set(p.display_group, g);
    }
    return [...m.values()].sort((a, b) => a.sira - b.sira);
  }, [siralilar]);

  const roller = useMemo(() => {
    const m = new Map<string, string>();
    (data ?? []).forEach((p) => m.set(p.role_code, p.role_name));
    return [...m.entries()];
  }, [data]);

  return (
    <AppShell>
      <div className="mb-4 flex items-center justify-between">
        <h1 style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>Personel</h1>
        <YeniPersonel />
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search
            size={16}
            strokeWidth={1.75}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 opacity-50"
          />
          <Input
            value={arama}
            onChange={(e) => setArama(e.target.value)}
            placeholder="Ad veya sicil ara"
            className="h-9 w-[220px] pl-8"
            aria-label="Personel ara"
          />
        </div>

        <select
          className="h-9 rounded-md border bg-card px-2 text-muted-foreground"
          value={rolFiltre}
          onChange={(e) => setRolFiltre(e.target.value)}
          aria-label="Rol filtresi"
        >
          <option value="">Tüm roller</option>
          {roller.map(([kod, ad]) => <option key={kod} value={kod}>{ad}</option>)}
        </select>

        <select
          className="h-9 rounded-md border bg-card px-2 text-muted-foreground"
          value={tipFiltre}
          onChange={(e) => setTipFiltre(e.target.value)}
          aria-label="Çalışma tipi filtresi"
        >
          <option value="">Tüm çalışma tipleri</option>
          {CALISMA_TIPI.map((c) => <option key={c.deger} value={c.deger}>{c.ad}</option>)}
        </select>

        {/* "Pasifleri göster" onay kutusu belirsizdi: dahil mi eder, yalnız
            onları mı gösterir? Üç durumlu filtre soruyu bırakmıyor. */}
        <select
          className="h-9 rounded-md border bg-card px-2 text-muted-foreground"
          value={durum}
          onChange={(e) => setDurum(e.target.value as never)}
          aria-label="Durum filtresi"
        >
          <option value="aktif">Aktif</option>
          <option value="pasif">Pasif</option>
          <option value="hepsi">Hepsi</option>
        </select>

        {satirlar.length !== (data?.length ?? 0) && (
          <span className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>
            {satirlar.length} / {data?.length} kişi
          </span>
        )}
      </div>

      <div className={bolunmus ? "flex min-h-0 flex-1 gap-4" : ""}>
      <div
        className={
          "overflow-auto rounded-lg border bg-card " +
          (bolunmus ? "w-[340px] shrink-0" : "")
        }
      >
        {error ? (
          <HataKutusu hata={error} onTekrar={() => refetch()} kisa />
        ) : isLoading ? (
          <p className="p-6 text-muted-foreground">Yükleniyor…</p>
        ) : satirlar.length === 0 ? (
          <p className="p-6 text-muted-foreground">Eşleşen kişi yok.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <Baslik alan="sicil" genislik="90px" sirala={sirala} onSirala={sirayaAl}>Sicil</Baslik>
                <Baslik alan="ad" genislik="200px" sirala={sirala} onSirala={sirayaAl}>Ad</Baslik>
                {!bolunmus && (
                  <>
                    <Baslik alan="soyad" genislik="170px" sirala={sirala} onSirala={sirayaAl}>Soyad</Baslik>
                    <Baslik alan="rol" genislik="210px" sirala={sirala} onSirala={sirayaAl}>Rol</Baslik>
                    <Baslik alan="grup" genislik="160px" sirala={sirala} onSirala={sirayaAl}>Grup</Baslik>
                    <Baslik alan="tip" genislik="150px" sirala={sirala} onSirala={sirayaAl}>Çalışma tipi</Baslik>
                    <Baslik alan="hedef" genislik="120px" sag sirala={sirala} onSirala={sirayaAl}>Aylık hedef</Baslik>
                    <TableHead>Durum</TableHead>
                  </>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Sicil, aylık hedef ve sözleşme tablodan çıktı: herkeste aynı ya da boş.
                  İkisi de detay panelinde duruyor (26.09 kararı). */}
              {gruplar.map((grup) => (
                <Fragment key={grup.ad}>
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={bolunmus ? 2 : 8} className="h-9 bg-background py-0">
                      <span
                        className="text-muted-foreground"
                        style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}
                      >
                        {grup.ad.toLocaleUpperCase("tr")}
                        <span className="ml-1.5 normal-case">({grup.satirlar.length})</span>
                      </span>
                    </TableCell>
                  </TableRow>

                  {grup.satirlar.map((p) => (
                    <TableRow
                      key={p.id}
                      className={
                        "h-11 cursor-pointer " +
                        (p.is_active ? "" : "opacity-55 ") +
                        (p.id === secili ? "bg-brand-soft " : "")
                      }
                      onClick={() => setSecili(p.id)}
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setSecili(p.id)}
                    >
                      <TableCell className="text-muted-foreground tabular-nums">
                        {p.sicil_no ?? "—"}
                      </TableCell>
                      <TableCell>
                        <span className="flex items-center gap-2.5">
                          <span
                            aria-hidden
                            className="flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
                            style={{ fontSize: "var(--text-xs)" }}
                          >
                            {basHarf(p.full_name)}
                          </span>
                          <span className="font-medium">
                            {bolunmus ? p.full_name : p.first_name}
                          </span>
                        </span>
                      </TableCell>
                      {!bolunmus && (
                        <>
                          <TableCell className="font-medium">{p.last_name}</TableCell>
                          <TableCell className="text-muted-foreground">{p.role_name}</TableCell>
                          <TableCell className="text-muted-foreground">{p.display_group}</TableCell>
                          <TableCell>
                            <Badge
                              variant="secondary"
                              className="h-5 rounded-sm px-1.5 font-normal"
                              style={{ fontSize: "var(--text-xs)" }}
                            >
                              {p.eligibility_label}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {p.monthly_target_hours == null ? "—" : `${p.monthly_target_hours} sa`}
                            {p.target_is_default && (
                              <span className="ml-1 text-muted-foreground"
                                    style={{ fontSize: "var(--text-xs)" }} title="Kural varsayılanı">
                                ·
                              </span>
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground">{p.status_label}</TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <DetayPaneli staffId={secili} herkes={data ?? []} onKapat={() => setSecili(null)} />
      </div>
    </AppShell>
  );
}

function YeniPersonel() {
  const [acik, setAcik] = useState(false);
  const [form, setForm] = useState({
    first_name: "", last_name: "", sicil_no: "",
    role_code: "hemsire", shift_eligibility: "gunduz_gece",
  });
  const qc = useQueryClient();
  const { data: roller } = useQuery({
    queryKey: ["roles"], queryFn: () => api<Role[]>("/people/roles"),
  });

  const ekle = useMutation({
    mutationFn: () =>
      api<PersonDetail>("/people", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ ...form, sicil_no: form.sicil_no || null }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["people"] });
      setAcik(false);
      setForm({ first_name: "", last_name: "", sicil_no: "", role_code: "hemsire", shift_eligibility: "gunduz_gece" });
    },
  });

  const gecerli = form.first_name.trim() && form.last_name.trim();

  return (
    <Dialog open={acik} onOpenChange={setAcik}>
      <DialogTrigger asChild>
        <Button>
          <Plus size={16} strokeWidth={1.75} />
          Personel ekle
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle style={{ fontSize: "var(--text-base)" }}>Personel ekle</DialogTitle>
        </DialogHeader>

        <div className="grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="grid gap-1.5">
              <Label style={{ fontSize: "var(--text-xs)" }}>Ad</Label>
              <Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
            </div>
            <div className="grid gap-1.5">
              <Label style={{ fontSize: "var(--text-xs)" }}>Soyad</Label>
              <Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Sicil</Label>
            <Input value={form.sicil_no} placeholder="isteğe bağlı"
                   onChange={(e) => setForm({ ...form, sicil_no: e.target.value })} />
          </div>
          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Rol</Label>
            <select className="h-9 w-full rounded-md border bg-card px-2" value={form.role_code}
                    onChange={(e) => setForm({ ...form, role_code: e.target.value })}>
              {(roller ?? []).map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}
            </select>
          </div>
          <div className="grid gap-1.5">
            <Label style={{ fontSize: "var(--text-xs)" }}>Çalışma tipi</Label>
            <select className="h-9 w-full rounded-md border bg-card px-2" value={form.shift_eligibility}
                    onChange={(e) => setForm({ ...form, shift_eligibility: e.target.value })}>
              {CALISMA_TIPI.map((c) => <option key={c.deger} value={c.deger}>{c.ad}</option>)}
            </select>
          </div>
          {ekle.isError && (
            <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>
              {(ekle.error as Error).message}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setAcik(false)}>İptal</Button>
          <Button onClick={() => ekle.mutate()} disabled={!gecerli || ekle.isPending}>
            {ekle.isPending ? "Ekleniyor…" : "Ekle"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

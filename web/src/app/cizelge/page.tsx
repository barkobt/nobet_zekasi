import { AppShell } from "@/components/shell/AppShell";

/** E-09 ana ekranı FAZ 2'de gelir. Bu yer tutucu kabuğun içinde durur. */
export default function CizelgeSayfasi() {
  return (
    <AppShell>
      <h1 className="mb-4" style={{ fontSize: "var(--text-lg)", fontWeight: 600 }}>
        Nöbet Çizelgesi
      </h1>
      <div className="rounded-lg border bg-card p-6">
        <p className="text-muted-foreground">Çizelge ızgarası hazırlanıyor.</p>
      </div>
    </AppShell>
  );
}

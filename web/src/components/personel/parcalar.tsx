import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
import { Label } from "@/components/ui/label";

/** Detay panelinin ortak küçük parçaları (DESIGN §5). */

export function Bolum({ baslik, children }: { baslik: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-4">
      <h3 className="text-muted-foreground"
          style={{ fontSize: "var(--text-xs)", letterSpacing: "0.04em" }}>
        {baslik.toLocaleUpperCase("tr")}
      </h3>
      <div className="grid gap-4">{children}</div>
    </section>
  );
}

export function Alan({ etiket, children }: { etiket: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <Label style={{ fontSize: "var(--text-xs)" }}>{etiket}</Label>
      {children}
    </div>
  );
}

export const Ikili = ({ children }: { children: React.ReactNode }) => (
  <div className="grid grid-cols-2 gap-4">{children}</div>
);

export const Bos = ({ children }: { children: React.ReactNode }) => (
  <p className="text-muted-foreground" style={{ fontSize: "var(--text-xs)" }}>{children}</p>
);

export const Hata = ({ children }: { children: React.ReactNode }) => (
  <p className="text-danger" style={{ fontSize: "var(--text-xs)" }}>{children}</p>
);

export function SatirKart({
  children, onSil, onDuzenle,
}: { children: React.ReactNode; onSil: () => void; onDuzenle?: () => void }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-md border px-3 py-2">
      <span className="min-w-0 flex-1">{children}</span>
      {onDuzenle && (
        <Button variant="ghost" size="sm" onClick={onDuzenle}>Düzenle</Button>
      )}
      <Button variant="ghost" size="icon" onClick={onSil} aria-label="Sil">
        <Trash2 size={16} strokeWidth={1.75} />
      </Button>
    </div>
  );
}

export function EkleDugmesi({
  children, onClick,
}: { children: React.ReactNode; onClick: () => void }) {
  return (
    <Button variant="outline" size="sm" onClick={onClick} className="justify-start">
      <Plus size={16} strokeWidth={1.75} />
      {children}
    </Button>
  );
}

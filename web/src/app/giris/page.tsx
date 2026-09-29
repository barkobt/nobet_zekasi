import { redirect } from "next/navigation";
import { cookies } from "next/headers";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const COOKIE = "clinorq_demo";

async function imza(parola: string): Promise<string> {
  const veri = new TextEncoder().encode(`clinorq:${parola}`);
  const ozet = await crypto.subtle.digest("SHA-256", veri);
  return Array.from(new Uint8Array(ozet))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default async function GirisSayfasi({
  searchParams,
}: {
  searchParams: Promise<{ devam?: string; hata?: string }>;
}) {
  const { devam = "/personel", hata } = await searchParams;

  async function girisYap(formData: FormData) {
    "use server";
    const parola = process.env.DEMO_PASSWORD ?? "";
    const girilen = String(formData.get("parola") ?? "");
    const hedef = String(formData.get("devam") ?? "/personel");

    if (!parola || girilen !== parola) {
      redirect(`/giris?devam=${encodeURIComponent(hedef)}&hata=1`);
    }
    (await cookies()).set(COOKIE, await imza(parola), {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 12,
    });
    redirect(hedef);
  }

  return (
    // DESIGN §4: giriş ekranı kabuğun dışında. Tek alan, tek birincil buton.
    <main className="flex h-dvh items-center justify-center bg-background">
      <form action={girisYap} className="w-[320px] rounded-lg border bg-card p-6">
        {/* DESIGN §4.1: giriş ekranında dikey kilit, açık zemin → -color varyantı.
            Logo zaten adı taşıdığı için yanına ayrıca ürün adı yazılmaz. */}
        <div className="mb-6 flex justify-center">
          <img
            src="/brand/clinorq/stacked/clinorq-stacked-color.svg"
            alt="Clinorq"
            className="h-14 w-auto"
          />
        </div>

        <label
          htmlFor="parola"
          className="mb-1.5 block text-muted-foreground"
          style={{ fontSize: "var(--text-xs)" }}
        >
          Demo şifresi
        </label>
        <Input id="parola" name="parola" type="password" autoFocus required />
        <input type="hidden" name="devam" value={devam} />

        {hata && (
          <p className="mt-2 text-danger" style={{ fontSize: "var(--text-xs)" }}>
            Şifre hatalı.
          </p>
        )}

        <Button type="submit" className="mt-4 w-full">
          Giriş
        </Button>
      </form>
    </main>
  );
}

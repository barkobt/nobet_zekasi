import { redirect } from "next/navigation";

/** FAZ 1'de personel listesi tek çalışan ekran; FAZ 2'de kök /cizelge'ye döner (DESIGN §6). */
export default function Home() {
  redirect("/personel");
}

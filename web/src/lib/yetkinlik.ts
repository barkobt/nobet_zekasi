import type { QueryClient } from "@tanstack/react-query";

/**
 * Yetkinlik iki ekrandan da değiştirilebiliyor: Personel > Yetkinlikler sekmesi
 * (kişi başına tam liste) ve Yetkinlik Matrisi (hücre hücre). İkisi ayrı sorgu
 * anahtarları kullandığı için biri yazınca diğeri bayat kalıyordu.
 *
 * Etkilenen HER anahtarı tek yerde geçersiz kılıyoruz: yeni bir ekran eklenirse
 * burası güncellenir, iki ekranın birbirinden habersiz kalması tekrarlanmaz.
 */
export function yetkinlikDegisti(qc: QueryClient) {
  qc.invalidateQueries({ queryKey: ["competency-matrix"] });
  qc.invalidateQueries({ queryKey: ["person"] });
  qc.invalidateQueries({ queryKey: ["people"] });
  // Yetkinlik çizelgedeki rozetleri ve kapsama sayılarını da belirliyor.
  qc.invalidateQueries({ queryKey: ["schedule"] });
}

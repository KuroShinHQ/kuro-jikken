# P1c - Mutfakta sakaroz cozunurlugu olcumu (protokol)

Bu, LLM'siz ilk gercek olcum. Amac yeni bir kimyasal iddia degil: **olcum
zincirini** (terazi, termometre, doygunluk karari) bilinen bir sistemde test
etmek. On kayit: `prereg/p1c_sucrose_solubility_plan_v1.md`.

## Ne gerekiyor

- 2 kg toz seker (tek marka)
- 1 g hassasiyetli mutfak terazisi
- 0-100 C termometre (varsa)
- tencere, ocak, kasik, zamanlayici
- `data/measurements/p1c_sucrose.csv` dosyasi

## On hazirlik (5 dk)

1. Teraziyi 100 g su ile test et: 100 +/- 2 g gostermeli.
2. Termometreyi kaynar suda kontrol et (95-100 C).
3. Tencerenin yarisindan fazlasini doldurma; sicak seker surubu ciddi yanik yapar.

## Bir nokta (yaklasik 15 dk)

1. **100 g su** tart, tencereye koy (olcu kabı degil, terazi).
2. Hedef sicakliga getir (20/40/60/80/90 C), +/-2 C'de tut; kapagi kapali, kisik ates.
3. Sekeri **10 g'lik** artislarla ekle; her seferinde 30 sn karistir, 60 sn bekle.
4. Iki sayiyi kaydet:
   - `last_dissolved_g`: tamamen cozunen son toplam (60 sn sonra kristal yok, berrak);
   - `first_residue_g`: 2 dk karistirmaya ragmen kristalin kaldigi ilk toplam.
5. Ayni sicaklikta **ikinci tekrar** icin tencereyi yika/kurut, adimi tekrarla.

## Tablo (10 nokta)

| Nokta | Sicaklik | Tekrar |
|---|---|---|
| P20 | 20 C | 1, 2 |
| P40 | 40 C | 1, 2 |
| P60 | 60 C | 1, 2 |
| P80 | 80 C | 1, 2 |
| P90 | 90 C | 1, 2 |

`data/measurements/p1c_sucrose.csv` satirlarini doldur:

- `temp_measured_c`: termometrenin gosterdigi gercek sicaklik
- `last_dissolved_g`, `first_residue_g`: yukaridaki iki sayi
- `notes`: "kapak acik", "buhar kacti" gibi notlar
- `measured_at`: tarih/saat

## Termometre yoksa (onceden ilan edilmis yedek)

Sadece **oda sicakligi (~20 C)** ve **kaynar su (~95-100 C)**, iki tekrar = 4 nokta.
Bu durumda sonuc "fallback 4-point" olarak raporlanir; 10 nokta sayilmaz.

## Analiz

```
.\.venv_inventory\Scripts\python.exe tools\p1c_analyze.py
```

Cikti: nokta tablosu, H1 (dogruluk, +/-%15), H2 (monoton artis), H3 (tekrar
farki <=%10), ortalama/maks hata ve PASS/FAIL. Bos satirlar atlanir; veri yoksa
`NO DATA` der ve sayi uretmez.

## Kural

- Olcum bitmeden hicbir sayi raporlanmaz.
- Bir nokta sadece dokulme/yanma/termometre arizasi/buharlasma icin cikarilir;
  referansa uymadigi icin cikarilmaz (on kayit §7).

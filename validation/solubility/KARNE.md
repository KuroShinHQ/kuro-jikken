# Karne - "suda ne kadar erir" tahminimiz ne kadar iyi?

Bu sayfa kimyager olmayan biri icin yazildi. Once sade fikir, sonra parantez icinde teknik ad.

## 1) Ne sinadik

Bir kumasin rengine, kalinligina ve dokusuna bakip "suyu ne kadar ceker" diye tahmin etmek gibi dusun: biz de molekulun yapisina bakip "suda ne kadar erir" diye tahmin eden kucuk bir formul (ESOL) sinadik. Tahminin adi "logS" (logS = suda cozunmenin 10 tabaninda logaritmasi; kucuk/negatif sayi = az erir, buyuk sayi = cok erir). Formul dort ipucu kullaniyor: yagi sevme derecesi (clogP), agirlik (molekul agirligi, MW), kac yerinden donebildigi (donen bag sayisi, RB) ve ne kadarinin halkali oldugu (aromatik oran, AP).

## 2) Sonuc tek bakista (dogrulama seti, 2.398 molekul)

Trafik isigi esikleri onceden plan.md dosyasinda yazildi; sonuca gore degistirilmedi.

| olcut | sonuc | isik |
|---|---|---|
| ortalama hata buyuklugu (RMSE) | 2.23 log birimi | KIRMIZI |
| tipik hata (MAE) | 1.22 log birimi | KIRMIZI |
| sistematik kayma (bias) | +0.13 log birimi | YESIL |
| hata <= 0.5 olanlarin orani | %32 | KIRMIZI |
| hata <= 1.0 olanlarin orani | %60 | KIRMIZI |

Sade ceviri: tahminlerimiz ortalama olarak 1.2 katip (log birimi) sasiriyor; 10 molekulden 3unde 0.5 birimden daha az sasiriyor. Bu, "kaba bir onsezi" seviyesinde; "laboratuvar yerine kullanilir" seviyesinde degil. Sistematik kayma yok (yesil): formul surekli yukari veya surekli asagi sapmiyor, iki yone de sasiriyor.

Grafikler: `fig_scatter.png` (tahmin vs olcum) ve `fig_hist.png` (hata dagilimi).

## 3) Nerede yaniliyor (molekul sinifi)

| sinif | molekul | tipik hata (MAE) | 1.0 icinde |
|---|---|---|---|
| asit | 294 | 0.93 | %69 |
| alkol | 393 | 0.96 | %68 |
| aromatik | 509 | 1.25 | %62 |
| halogenli | 96 | 1.45 | %62 |
| amin | 676 | 1.25 | %54 |
| diger | 430 | 1.51 | %50 |

En iyi: asitler ve alkoller (kucuk, polar molekuller). En kotu: "diger" grubu - formulun dort ipucunun da zayif kaldigi karisik molekuller.

## 4) Ayar oncesi / sonrasi fark

Ayni formul, katsayilar sadece ayar setinde yeniden hesaplandi (P-B): RMSE 2.23 -> 1.85 (iyilesti), fakat tipik hata 1.22 -> 1.26 ve "1.0 icinde" orani %60 -> %52 (kotulesti). Dürüst hukum: **yeniden hesaplama belirgin bir kazanc getirmedi; bazi metriklerde kotulesti.**

## 5) Kilitli sinav (bir kez, 25.10.2026)

Kilit hash dogrulandi (LOCK.sha256), LOCK_ACCESS_LOG.md dosyasina zamanli kayit dusuldu; kilitli set 2.399 molekul.

| olcut | P-A | P-B |
|---|---|---|
| RMSE | 2.14 | 1.85 |
| tipik hata (MAE) | 1.19 | 1.24 |
| bias | +0.19 | -0.06 |
| <=0.5 icinde | %32 | %28 |
| <=1.0 icinde | %59 | %52 |

On-kayitli tahminlerin karnesi:

- P1 (tum veri RMSE 2.23 +/- 0.3): **TUTTU** - 2.14 (-0.09).
- P2 (hedef alan RMSE 1.22 +/- 0.2): **TUTTU** - 1.225 (fark ~0.003).
- P3 (refit 0.1den fazla iyilestirmez): **TUTTU, ama ters yonde** - hedef alanda P-B 1.401, yani 0.176 KOTULESTI.
- P4 (tuz/metal yine >3.0): **TUTTU** - tuz/karisim 5.27, metal 4.99.

Sade ceviri: kilitli sinav, dogrulama setindeki kirmizi karneyi tekrarladi; hedef alandaki "orta karar" dogruluk (1.22-1.23) da iki sette neredeyse ayni cikti. Formul, tuz/metal/karisimlarda hala cok kotu.


## 6) Bu sonuc neyi KANITLAMAZ

- "ESOL kotu bir formul" demek icin yeterli degil: AqSolDB bilerek genis (tuzlar, metaller, cok buyuk molekuller). ESOL ise kucuk, notr, karbonlu molekuller icin tasarlandi.
- Bu bir "laboratuvar dogrulugu" iddiasi degil: yalnizca tek bir genis veri setinde, tek bir formulun kaba dogrulugunu olctuk.
- Baslangicta yazilan kural degismedi; hicbir molekul sonradan atilmadi.

## Kesif bolumu (sonradan yapilan analiz - on-kayitli degil)

Sonuclari gordukten sonra (25.10.2026) yapilan ayri bir inceleme: hatalarin cogu ESOL formulunun hedef alani disindaki molekullerden geliyor. On kayitli sonuc yukarida oldugu gibi kalir; bu bolum yalnizca aciklama.

| grup | molekul | tipik hata (MAE) |
|---|---|---|
| metal iceren | 60 | 3.87 |
| tuz/karisim (nokta iceren) | 761 | 2.91 |
| cok agir (MW>500) | 205 | 2.51 |
| yuklu (iyon) | 450 | 1.07 |
| notr, tek parca, <=500 | 5,718 | 0.93 |

Yani "gercek hedef kitlemiz" olan notr kucuk molekullerde tipik hata 0.93; karneyi kirmizi yapan sey, formulun hic hedeflemedigi tuz/metal/agir molekuller.

Oneri (henuz UYGULANMADI): bir sonraki turda "uygulanabilirlik alani" kurali - tek parca, notr, metalsiz, MW<=500. Karari birlikte verecegiz; dosya: `AMENDMENT_PROPOSAL.md`.

Ayrintili tablo ve en kotu 20 tahmin: `exploratory.md`.

## Duzeltme kontrolu (cetvel saglam mi?)

Formulu orijinal Delaney setinde (1.128 molekul) calistik: RMSE 1.10, tipik hata 0.84; yayindaki deger ~1.0 civari. Yani kod dogru; AqSolDB genis oldugu icin karne kirmizi. Ayrinti: `sanity_delaney.md`.


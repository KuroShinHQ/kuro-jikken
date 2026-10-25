import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
f = sorted(HERE.glob("preds_validation_*.csv"))[-1]
rows = list(csv.DictReader(open(f, encoding="utf-8")))
meas = [float(r["measured"]) for r in rows]
pa = [float(r["P_A"]) for r in rows]
pb = [float(r["P_B"]) for r in rows]

plt.figure(figsize=(6, 6))
plt.scatter(meas, pa, s=6, alpha=0.35, label="Yayinlanmis katsayilar (P-A)")
plt.scatter(meas, pb, s=6, alpha=0.35, label="Ayar verisiyle yeniden (P-B)")
plt.plot([-12, 2], [-12, 2], "r--")
plt.xlabel("Olculen (logS)"); plt.ylabel("Tahmin (logS)")
plt.legend(); plt.tight_layout()
plt.savefig(HERE / "fig_scatter.png", dpi=150); plt.close()

err = [a - b for a, b in zip(pa, meas)]
plt.figure(figsize=(6, 4))
plt.hist(err, bins=40)
plt.xlabel("Hata (tahmin - olcum, log birimi)"); plt.ylabel("Molekul sayisi")
plt.tight_layout()
plt.savefig(HERE / "fig_hist.png", dpi=150); plt.close()
print("figures OK", f.name)

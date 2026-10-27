// GENERATED FILE - do not edit by hand.
// Generator: .opencode/skills/lab/scripts/gen_model.py
// Source:    data/labs/al_cu_liquidus_r3.json (baked 2026-10-27T02:33:27, head 2e21943)
// Every anchor below is one ledger entry produced by bake.py -> mcp/pipeline.ask.

export const TOLERANCE_K = 0.5

export const META = {
  engine: "pycalphad equilibrium (Al-Cu liquidus)",
  dataset: "mc_al_v2.032.pycalphad.tdb",
  created: "2026-10-27T02:33:27",
  head: "2e21943",
  source: "data/labs/al_cu_liquidus_r3.json",
  points: 21,
}

// e = half of the bisection bracket (numerical resolution), null when the point
// was solved on the pure-element path and no bracket exists.
export const ANCHORS = [
  { cu: 0.0, k: 933.47, e: 0.0427, id: "20261026T233204-f40e097a" },
  { cu: 0.5, k: 931.884765625, e: 0.341796875, id: "20261026T233208-e570ada1" },
  { cu: 1.0, k: 930.517578125, e: 0.341796875, id: "20261026T233213-ecdcb4c8" },
  { cu: 1.5, k: 929.150390625, e: 0.341796875, id: "20261026T233217-6b962052" },
  { cu: 2.0, k: 927.783203125, e: 0.341796875, id: "20261026T233221-435ddb5d" },
  { cu: 2.5, k: 926.416015625, e: 0.341796875, id: "20261026T233225-97f3805d" },
  { cu: 3.0, k: 925.048828125, e: 0.341796875, id: "20261026T233230-d31dcae2" },
  { cu: 3.5, k: 922.998046875, e: 0.341796875, id: "20261026T233234-9387a0c5" },
  { cu: 4.0, k: 921.630859375, e: 0.341796875, id: "20261026T233238-b02945d1" },
  { cu: 4.5, k: 920.263671875, e: 0.341796875, id: "20261026T233242-ce0052f1" },
  { cu: 5.0, k: 918.896484375, e: 0.341796875, id: "20261026T233246-f7643683" },
  { cu: 5.5, k: 917.529296875, e: 0.341796875, id: "20261026T233251-a85ac4b0" },
  { cu: 6.0, k: 916.162109375, e: 0.341796875, id: "20261026T233254-236b2af9" },
  { cu: 6.5, k: 914.111328125, e: 0.341796875, id: "20261026T233258-4dcb762e" },
  { cu: 7.0, k: 912.744140625, e: 0.341796875, id: "20261026T233303-c770ed5d" },
  { cu: 7.5, k: 911.376953125, e: 0.341796875, id: "20261026T233307-13cffd28" },
  { cu: 8.0, k: 910.009765625, e: 0.341796875, id: "20261026T233311-40c268a7" },
  { cu: 8.5, k: 908.642578125, e: 0.341796875, id: "20261026T233315-3822b2c5" },
  { cu: 9.0, k: 906.591796875, e: 0.341796875, id: "20261026T233319-ff039e6d" },
  { cu: 9.5, k: 905.224609375, e: 0.341796875, id: "20261026T233323-c4b77968" },
  { cu: 10.0, k: 903.857421875, e: 0.341796875, id: "20261026T233327-a4720ad1" },
]

export const REFUSAL = {
  sentence: "Bu madde/veri seti elimizde yok; en yakin kapsam: alloy.phase",
  ledger: "20261026T225932-91f72739",
  gate: "RED",
  reason: "no data",
}

// What the answer does not say, verbatim from the ledger entry (limits are not prose we invented).
export const LIMITS = [
  "liquidus of 2.0 wt% Cu = mole fraction x(Cu) = 0.00859; Al-Cu database phases only",
  "\u00b10.342 K is the bisection bracket (numerical resolution), not database or model uncertainty",
]

export function inDomain(cu) {
  return Number.isFinite(cu) && cu >= ANCHORS[0].cu && cu <= ANCHORS[ANCHORS.length - 1].cu
}

/**
 * The page model. An anchor is returned untouched (k, e, id come from the ledger).
 * Between anchors it interpolates linearly and says so: `exact: false` and a
 * declared +-TOLERANCE_K. Out of domain it returns null - the page then shows the
 * refusal sentence and no number at all.
 */
export function liquidus(cu) {
  if (!inDomain(cu)) return null
  const exact = ANCHORS.find((a) => a.cu === cu)
  if (exact) return { k: exact.k, exact: true, e: exact.e, id: exact.id, tol: 0 }
  for (let i = 1; i < ANCHORS.length; i++) {
    const a = ANCHORS[i - 1], b = ANCHORS[i]
    if (cu > a.cu && cu < b.cu) {
      const t = (cu - a.cu) / (b.cu - a.cu)
      return {
        k: a.k + t * (b.k - a.k), exact: false, tol: TOLERANCE_K,
        kLow: a.k, kHigh: b.k, idLow: a.id, idHigh: b.id,
      }
    }
  }
  return null
}

# Phase 2 P2-B materiality inventory

**[PROBE — not for citation]**

## Question

Which physical and structural signals used to assess cuneiform joins are encoded in TLHdig, and which are absent?

## What I did

Scanned aggregate tag/attribute names for 20,762 filename-gated non-test XML files and measured the governed non-test edge universe (21,942 fragments; 363,524 embedded lines). Test entries were skipped before decompression. The checklist is cross-referenced to Würzburg/HPM 3D-join work, the observed-reconstruction study, and ORACC's direct/indirect join distinction.

## What I found

| signal | corpus status | measured coverage / limitation |
|---|---|---|
| line order and labels | usable symbolic | 100.0% of fragment lines; no metric coordinates |
| side / column | partial proxy | 67.3% / 51.1% of lines |
| rulings / paragraphs | usable symbolic | `parsep` in 80.7% of safe XML documents; no ruling geometry |
| gaps, blank widths, edge damage | partial proxy | gaps in 98.1% of documents; editorial encoding, not a measured fracture |
| explicitly preserved physical edge | sparse direct | 0.5% of fragment lines carry an edge direction |
| publication / inventory / site | partial proxy | inventory number in 5.9%; prefix-site recognized for 90.5%; no locus/room/stratigraphy |
| editorial direct/indirect relation | label only | encoded, but not independent physical evidence or certainty |
| photos, drawings, 3D mesh, point cloud | absent | zero media/3D files in the distributed archive |
| dimensions, thickness, curvature, break contour | absent | no safe-schema field or metric coordinate payload |
| clay colour/fabric/composition | absent | no safe-schema field |
| wedge shape, ductus, paleography, ancient hand | absent | sign identity survives only through editorial transliteration |

## What it rules in / rules out

TLHdig can support symbolic layout compatibility, damage-aware abstention, coarse provenance controls, and textual-affinity work. It cannot support a genuinely material physical-join model: the highest-value channels identified by 3D-join research—contour, surface geometry, dimensions, clay appearance/composition, and graphetic hand—are absent. Tier-A no-overlap work should therefore default to `insufficient encoded evidence` unless a textual bridge or an external material-data module is available.

No content scoring occurred, so the tracer block is not applicable.

## Cost

11.2 seconds elapsed against a 2-hour budget.

## Falsifier

This conclusion would be wrong if material measurements are linked to TLHdig through an external identifier/resource not represented in the distributed archive or governed derived artifacts.

## Sources

- [Würzburg 3D-Joins und Schriftmetrologie](https://www.phil.uni-wuerzburg.de/altorientalistik/forschung/abgeschlossene-forschungsvorhaben/3d-joins-und-schriftmetrologie/)
- [Hethitologie-Portal Mainz 3D-Joins](https://www.hethport.uni-wuerzburg.de/HPM/hpm.php?p=3djoins)
- [Observed methods of cuneiform tablet reconstruction](https://www.sciencedirect.com/science/article/pii/S0305440314003690)
- [Nineveh Medical Project: About the sources](https://oracc.museum.upenn.edu/asbp/ninmed/Aboutthesources/index.html)

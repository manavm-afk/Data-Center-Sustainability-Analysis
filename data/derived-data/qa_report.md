# QA Report — preprocessing pipeline

Generated 2026-07-10 by code/preprocessing.py. Methods in METHODS.md.

## Headline numbers — before/after

| Metric | Old pipeline (state-dict water, nearest-plant grid) | New pipeline |
|---|---|---|
| Facilities | 1474 | 1474 |
| Mean CO2 rate, unweighted (lb/MWh) | 704.5 | 704.3 |
| Mean CO2 rate, sqft-weighted (lb/MWh) | — | 785.6 |
| Facilities in High/Extremely High water stress | 393 (26.7%) | 511 (34.7% of facilities with data) |
| Dual-risk facilities (>700 lb/MWh AND High/Extremely High) | 250 | 284 |
| Top 3 states | {'VA': 319, 'TX': 127, 'CA': 112} | {'VA': 319, 'TX': 127, 'CA': 112} |

Arid-basin facilities: 0; No Data: 0 (excluded from the high-stress denominator).

## Water-stress join (merge_method)

| merge_method | facilities |
|---|---|
| hydrobasins_pip | 1474 |

## eGRID subregion assignment (egrid_assignment_method)

| egrid_assignment_method | facilities |
|---|---|
| pip | 1437 |
| pip_overlap_plant_tiebreak | 37 |

Legacy nearest-plant method vs point-in-polygon: 16/1474 facilities would have been assigned a different subregion (1.1%).

Top reassignments (nearest-plant -> PIP):

| key | facilities |
|---|---|
| RFCE -> SRVC | 7 |
| ERCT -> SRMV | 3 |
| NWPP -> AZNM | 1 |
| RFCE -> RFCW | 1 |
| RFCW -> SRTV | 1 |
| RMPA -> NWPP | 1 |
| SRMV -> SRTV | 1 |
| SRTV -> SRMV | 1 |

Old (nearest-plant) vs new (PIP) subregion disagreement: 17/1474 facilities (1.2%).

Top disagreeing pairs (old -> new):

| key | facilities |
|---|---|
| RFCE -> SRVC | 7 |
| ERCT -> SRMV | 3 |
| NEWE -> NYUP | 1 |
| NWPP -> AZNM | 1 |
| RFCE -> RFCW | 1 |
| RFCW -> SRTV | 1 |
| RMPA -> NWPP | 1 |
| SRMV -> SRTV | 1 |

## FracTracker capacity match

- Matched facilities (<=500 m, one-to-one): 327
- Median match distance: 34 m
- MW known: 87 (5.9% of all facilities)
- Operator-name mismatches (report-only): 88

## Spot checks

- [PASS] All Loudoun County VA facilities -> SRVC — {'SRVC': 213}
- [PASS] Grant County WA facilities -> NWPP — {'NWPP': 39}
- [PASS] Puerto Rico facilities -> PRMS via hydrobasins_pip — subregions=['PRMS'], methods=['hydrobasins_pip']
- [PASS] Maricopa County AZ facilities in High/Extremely High/Arid basins — {'Extremely High': 58, 'High': 5}
- [INFO] Santa Clara CA: old fake score was 4.0 ('Extremely High' by state dict); new basin values: score mean 1.29, categories {'Low-Medium': 75}

## Invariants

- Arid facilities labeled 'Extremely High (>80%)': 0 (must be 0)
- Non-canonical bws_label values: none
- Non-arid facilities with bws_raw > 100 (9999 contamination): 0 (must be 0)

## Result: ALL CHECKS PASSED

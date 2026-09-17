# Nutrition rules, safety, and Registry

Status: current calculation, safety, Registry, and evaluation authority.

## Numeric policy

Calculations convert inputs to `Decimal` from strings. BMR/TDEE retain two decimals
for response; final calories use whole-number round-half-even; macro and configured
nutrient targets use Registry precision with round-half-even. The authoritative Diary
calendar timezone is `Asia/Riyadh`.

## Energy

Age is Gregorian age on the authoritative effective date.

Mifflin–St Jeor BMR:

- base = `10 × weight_kg + 6.25 × height_cm − 5 × age`
- male offset `+5`; female offset `−161`

TDEE is BMR multiplied by activity factor:

| Level | Factor |
|---|---:|
| sedentary | 1.2 |
| light | 1.375 |
| moderate | 1.55 |
| active | 1.725 |
| very_active | 1.9 |

Maintain uses TDEE. Bulk uses `TDEE × 1.1`. Cut accepts intensity 0.15, 0.20,
or 0.25 and subtracts `min(TDEE × intensity, 750 kcal)`.

## Macros

- Protein input is 1–3 g/kg. Below BMI 30 it uses actual weight. At BMI 30 or
  above it uses `reference_weight + 0.33 × (actual − reference)`, where reference
  weight is `BMI 25 × height_m²`.
- Fat is `final calories × fat_pct ÷ 9`; allowed fat input is 0.15–0.40 with
  defaults 0.25 male and 0.30 female.
- Carbohydrate is `(final calories − raw protein grams × 4 − final calories × fat_pct) ÷ 4`.
  A non-positive result is rejected. Below 100 g yields a warning; 100–129.9 g
  yields an informational warning against the 130 g general reference.

## Safety

| Final calories | Outcome | Save allowed |
|---|---|---:|
| greater than 1200 | `normal` | Yes |
| 800 through 1200 | `specialist_review_required` | No |
| below 800 | `very_low_energy_blocked` | No |

The Backend owns the outcome and rejects blocked TargetPlan writes. The frontend must
not recreate safety calculations or provide acknowledgment/override.

Exact current Arabic messages, verified against frontend behavior and E2E tests:

- `SPECIALIST_REVIEW_REQUIRED`: `لا يمكن حفظ هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.`
- `VERY_LOW_ENERGY_TARGET_BLOCKED`: `لا يمكن حفظ هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.`

They appear in the preview, focused safety explanation after a blocked attempt, and
Backend-rejection recovery UI. They are not generic network errors.

## Registry

The Backend Registry owns nutrient keys, storage fields, Arabic labels, units,
precision/order, target type/source/rule, completeness/Diary-coverage participation,
Food taxonomy, and nutrition-source labels. Required core Food values are calories,
protein, carbohydrate, and fat. Optional nutrient null means unknown; it never means zero.

Supported target types are minimum, maximum, adequate, recommended, range,
monitor-only, and minimize. Structural validation requires the expected collections
and fields, valid types/definitions, unique nutrient keys, and valid taxonomy pairs.
The frontend consumes this payload rather than maintaining another Registry.

## Integrity and preview binding

The canonical rules manifest contains calculation policy, nutrients, target types,
primary categories/taxonomy, and nutrition-source definitions. Canonical sorted JSON
is SHA-256 hashed as `rules_manifest_hash`; the Registry endpoint uses it as content
fingerprint/ETag. `rules_manifest.lock.json` pins released content and CI rejects drift.

`preview_hash` covers normalized Profile inputs, effective date, calculated result,
and `rules_manifest_hash`. A rule/content change therefore invalidates a stale preview
even if visible numeric output is unchanged. TargetPlan writes also retain independent
idempotency request hashes.

## Nutrient targets and evaluation

Current calculated targets include fiber 30 g; added sugar at most 10% calories;
saturated fat at most 10%; trans fat at most 1%; sodium 2000 mg; potassium 3400 mg
male/2600 mg female; sex/age-specific calcium, iron, magnesium, zinc and vitamin A;
and fixed selenium 55 mcg, B12 2.4 mcg, folate DFE 400 mcg, and iodine 150 mcg.
Cholesterol is monitor-only with no calculated numeric target.

Diary coverage states:

- no entries: `no_entries`, percentage null;
- entries but all values unknown: `all_unknown`, 0%;
- known and unknown values: `partial`; incomplete results never claim an unmet lower
  bound or safe upper-bound availability;
- all participating values known: `complete`, 100%, with normal evaluation/progress.

Known zero is known data. Minimum/recommended/adequate use at-least evaluation;
maximum uses within/exceeded; range evaluates bounds; monitor-only has no progress,
remaining, or available claim. Remaining/available values never become negative.

## Compact golden examples

- Male, 80 kg, 180 cm, age 30: BMR = 1780; moderate TDEE = 2759.
- At TDEE 2759 with 20% cut: requested/applied deficit = 551.8; final calories = 2207.
- A requested cut deficit above 750 is capped at 750 and reports the cap.
- BMI below 30 uses actual protein weight; BMI exactly 30 uses adjusted weight.
- Rule-manifest changes change `preview_hash` even when target calories do not.
- `[5, 0, null, 3]` is 75% partial coverage; `[0]` is complete known-zero coverage.

## Retired versioning

No active calculation-engine, Registry, Registry-schema, or calculation-document
semantic version exists in persistence, APIs, new calculation documents, or frontend
compatibility gates. Historical embedded TargetPlan JSON keys remain inert and are not
rewritten. Integrity is provided by stored calculated output, immutable TargetPlans,
structural validation, manifest hash/lock, preview hash, and tests.

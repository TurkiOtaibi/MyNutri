# H03 Approved Arabic Safety Messages

## 1. Decision identity

| Field | Value |
|---|---|
| Document ID | `DEC-H03-20` |
| Decision title | Arabic safety messages for blocked target activation |
| Decision status | Approved |
| Approval date | 2026-07-24 |
| Product Owner approval role | Product Owner — approved the exact messages and code mapping |
| Arabic content reviewer role | Arabic content reviewer — approved the Arabic wording for implementation and testing |
| Lifecycle status | Frozen for implementation and testing |

## 2. Decision scope

This decision freezes the exact Arabic messages presented when the authoritative Backend prevents Target Plan activation for either of these safety outcomes:

- `SPECIALIST_REVIEW_REQUIRED`
- `VERY_LOW_ENERGY_TARGET_BLOCKED`

It resolves the Arabic-content approval gate for Plan 005 only. It does not change calculations, calorie boundaries, Backend enforcement, API contracts, or implementation scope.

## 3. Frozen code-to-message mapping

### `SPECIALIST_REVIEW_REQUIRED`

لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.

### `VERY_LOW_ENERGY_TARGET_BLOCKED`

لا يمكن تفعيل هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.

The two Arabic strings above are exact test oracles. Implementation and automated tests must use them verbatim without rewriting, shortening, punctuation changes, or client-side substitutions.

## 4. Approved presentation locations

Each message appears in all of the following locations for its corresponding authoritative outcome or Backend rejection:

- The preview card.
- The named safety-explanation element that receives focus after a blocked attempt.
- The recovery interface after Backend rejection.

## 5. Blocking behavior

Both outcomes block all of the following:

- Opening the confirmation dialog.
- Sending the activation POST.
- Any acknowledgment path.
- Any override path.

The draft and authoritative preview remain available so the user can understand the result or change inputs. The blocked state must not be presented as a generic network or save failure.

## 6. Authority and content constraints

The Backend is the sole source of truth for the safety outcome, `can_activate`, calculation result, and activation rejection. The frontend maps the authoritative code to the frozen Arabic message and must not infer the outcome from calorie values or recreate safety calculations.

The approved messages:

- Do not provide a diagnosis.
- Do not provide a treatment promise.
- Do not imply that a specialist service exists inside the application.
- Do not provide an acknowledgment, override, or any other bypass path.

## 7. Recorded approval

```text
Decision status: Approved
Product Owner approval role: Recorded
Arabic content reviewer role: Recorded
Approval date: 2026-07-24
Implementation authority: Backend
Confirmation dialog for either blocked outcome: Prohibited
Activation POST for either blocked outcome: Prohibited
Acknowledgment or override: Prohibited
Decision status: Frozen for implementation and testing
```

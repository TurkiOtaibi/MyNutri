# V2 Shared Food Catalog

Status: current authority

## One catalog and one experience

Food visibility is global. `/foods` is the only Food catalog experience:

- authenticated users browse, search, filter, sort, inspect, and select Foods for Diary use;
- administrators use that same surface and additionally see Add, Edit, and Delete controls;
- `/admin/foods` does not exist; `/foods` is the sole Food UI route;
- the Admin home retains user monitoring and has no separate Food Management tile.

The backend remains authoritative. `POST /foods`, `PUT /foods/{food_id}`, and
`DELETE /foods/{food_id}` require the admin role even when a client constructs a
request directly. Read operations remain available to authenticated users.
`GET /foods` always returns the paginated `FoodListResponse`; there is no
legacy bare-array response, uncategorized sentinel, or versioned `Food*V3`
schema alias.

## Food truth and Diary measurement

Food nutrition and other mutable catalog data are current authoritative truth.
Diary totals calculate from the current Food record and the entry's recorded
consumed amount. A Diary entry retains its recorded unit type, amount, basis,
and optional label so later serving-default edits do not change what was
consumed. A referenced Food cannot change between mass and volume nutrition
dimensions.

## Permanent deletion

Food Archive, Restore, archived views, and lifecycle status do not exist.
`archived_at` and `archived_by_principal_id` are not part of the model or API.

Admin Delete permanently removes the global Food and, in the same database
transaction, every `diary_entry` that references it across every Principal.
`diary_entry.food_id` is non-null and uses `ON DELETE CASCADE`. This destructive
cross-user history loss is intentional. Unrelated Diary entries and all Target
Plans remain unchanged. No Food-deletion audit event, tombstone, or recovery
record is created.

The exact approved confirmation is:

- Title: `حذف الطعام؟`
- Body: `سيتم حذف هذا الطعام نهائيًا، كما سيتم حذف جميع سجلات اليوميات المرتبطة به لجميع المستخدمين. لا يمكن التراجع عن هذا الإجراء.`
- Buttons: `إلغاء` / `حذف نهائي`

## Database access

The FastAPI admin dependency is the mutation authority. Direct Food-table
mutation privileges are revoked from `PUBLIC`, `anon`, and `authenticated`.
The established backend database role retains the access required to serve the
API. Broader `diary_entry` Data API privilege design is outside this cutover.

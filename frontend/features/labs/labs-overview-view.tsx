import Link from "next/link";

import type { LabCatalogResponse, LabOverviewResponse } from "@/lib/types";
import type { LabListItem, LabSort } from "./lab-model";
import styles from "./labs.module.css";

type LabsViewProps = {
  catalog: LabCatalogResponse;
  rows: LabListItem[];
  eligibility: LabOverviewResponse["eligibility"];
  search: string;
  category: string | null;
  sort: LabSort;
  readOnly: boolean;
  onSearchChange: (value: string) => void;
  onCategoryChange: (value: string | null) => void;
  onSortChange: (value: LabSort) => void;
};

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("ar-SA-u-ca-gregory", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function EligibilityNotice({ eligibility }: { eligibility: LabsViewProps["eligibility"] }) {
  if (eligibility.allowed) return null;
  if (eligibility.reason === "profile_required") {
    return <div className={styles.notice}><span>أكمل ملفك قبل تسجيل نتائج التحاليل.</span><Link className="btn primary" href="/profile">إكمال الملف</Link></div>;
  }
  if (eligibility.reason === "adult_only") {
    return <p className={styles.notice}>تسجيل نتائج التحاليل متاح للبالغين فقط.</p>;
  }
  return null;
}

function Controls({ catalog, search, category, sort, onSearchChange, onCategoryChange, onSortChange }: LabsViewProps) {
  return <div className={styles.controls}>
    <label className={styles.searchField}>
      <span>البحث في التحاليل</span>
      <input type="search" value={search} onChange={(event) => onSearchChange(event.target.value)} />
    </label>
    <label>
      <span>التصنيف</span>
      <select value={category ?? ""} onChange={(event) => onCategoryChange(event.target.value || null)}>
        <option value="">كل التصنيفات</option>
        {catalog.categories.map((item) => <option key={item.key} value={item.key}>{item.name_ar}</option>)}
      </select>
    </label>
    <label>
      <span>الترتيب</span>
      <select value={sort} onChange={(event) => onSortChange(event.target.value as LabSort)}>
        <option value="newest_updated">الأحدث تحديثًا</option>
        <option value="oldest_updated">الأقدم تحديثًا</option>
        <option value="name_asc">الاسم تصاعديًا</option>
        <option value="name_desc">الاسم تنازليًا</option>
        <option value="category">التصنيف</option>
      </select>
    </label>
  </div>;
}

function LabRows({ rows, emptyMessage }: { rows: LabListItem[]; emptyMessage: string }) {
  if (rows.length === 0) return <div className={styles.empty}><strong>{emptyMessage}</strong><span>يمكنك تغيير البحث أو التصنيف لعرض نتائج أخرى.</span></div>;
  return <ul className={styles.rows}>
    {rows.map((item) => <li
      key={item.test_key}
      className={styles.row}
      data-testid="lab-row"
      data-test-key={item.test_key}
      data-category={item.test.primary_category}
    >
      <div className={styles.identity}>
        <strong>{item.test.name_ar}</strong>
        <span dir="ltr">{item.test.abbreviation ?? item.test.name_en}</span>
      </div>
      {item.latest ? <div className={styles.latest}>
        <strong dir="ltr">{item.latest.display_value} {item.latest.display_unit}</strong>
        <span className={styles.status} data-tone={item.latest.status.tone}>{item.latest.status.label_ar}</span>
        <time dateTime={item.latest.test_date}>{formatDate(item.latest.test_date)} · {item.latest.test_date}</time>
      </div> : <span className={styles.noResult}>لا توجد نتيجة مسجلة</span>}
    </li>)}
  </ul>;
}

function LabsView(props: LabsViewProps & { mode: "owned" | "catalog" }) {
  const emptyMessage = props.category
    ? props.mode === "owned" ? "لا توجد نتائج ضمن هذا التصنيف." : "لا توجد تحاليل ضمن هذا التصنيف."
    : props.search ? "لا توجد تحاليل مطابقة." : "لم تسجل أي نتائج بعد.";
  return <section className={styles.panel} aria-label={props.mode === "owned" ? "نتائج التحاليل" : "كتالوج التحاليل"}>
    <EligibilityNotice eligibility={props.eligibility} />
    <Controls {...props} />
    <div className={styles.resultBar}><span>{props.rows.length} تحليلاً</span>{props.readOnly ? <strong>للقراءة فقط</strong> : null}</div>
    <LabRows rows={props.rows} emptyMessage={emptyMessage} />
  </section>;
}

export function OwnedLabsView(props: LabsViewProps) {
  return <LabsView {...props} mode="owned" />;
}

export function LabCatalogView(props: LabsViewProps) {
  return <LabsView {...props} mode="catalog" />;
}

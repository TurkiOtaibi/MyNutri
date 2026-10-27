import { ApiError } from "./api";

export type AccountAction = "create" | "retry-create" | "edit" | "password" | "status" | "delete" | "retry-delete";

const failures: Record<AccountAction, string> = {
  create: "تعذر إكمال إنشاء المستخدم. أعد المحاولة.",
  "retry-create": "تعذر إكمال إنشاء المستخدم. أعد المحاولة.",
  edit: "تعذر حفظ تغييرات المستخدم. حاول مرة أخرى.",
  password: "تعذر إعادة تعيين كلمة المرور. حاول مرة أخرى.",
  status: "تعذر تحديث حالة المستخدم. حاول مرة أخرى.",
  delete: "تعذر إكمال حذف المستخدم. لا يستطيع الدخول الآن، ويمكنك إعادة المحاولة.",
  "retry-delete": "تعذر إكمال حذف المستخدم. لا يستطيع الدخول الآن، ويمكنك إعادة المحاولة.",
};

const successes: Record<AccountAction, string> = {
  create: "تم إنشاء المستخدم.",
  "retry-create": "تم إنشاء المستخدم.",
  edit: "تم حفظ تغييرات المستخدم.",
  password: "تمت إعادة تعيين كلمة المرور.",
  status: "تم تحديث حالة المستخدم.",
  delete: "تم حذف المستخدم نهائيًا.",
  "retry-delete": "تم حذف المستخدم نهائيًا.",
};

export function accountActionErrorMessage(error: unknown, action: AccountAction): string {
  if (error instanceof ApiError && error.code === "DELETION_INCOMPLETE") return failures.delete;
  if (error instanceof ApiError && error.code === "CREATION_IN_PROGRESS") return "لا يمكن حذف المستخدم الآن لأن إنشاءه ما زال جاريًا. حاول بعد 5 دقائق.";
  if (error instanceof TypeError || (error instanceof ApiError && error.status === 0)) {
    return "تعذر الاتصال بالخادم. حاول مرة أخرى.";
  }
  if (error instanceof ApiError && error.code !== "CREATION_INCOMPLETE" && error.message !== failures.create && error.message && !error.message.startsWith("API request")) {
    return error.message;
  }
  return failures[action];
}

export function accountActionSuccessMessage(action: AccountAction): string {
  return successes[action];
}

export function passwordValidationMessage(value: string): string {
  return Array.from(value).length < 8 ? "كلمة المرور قصيرة. استخدم 8 أحرف على الأقل." : "";
}

export function usernameValidationMessage(value: string): string {
  if (!value.trim()) return "أدخل اسم المستخدم.";
  return /^[A-Za-z0-9._-]{3,32}$/.test(value.trim()) ? ""
    : "استخدم من 3 إلى 32 حرفًا لاسم المستخدم: أحرف إنجليزية أو أرقام أو . أو _ أو - فقط.";
}

export function deletionConfirmationMessage(value: string, account: { username?: string | null; email?: string | null }): string {
  const identity = account.username ?? account.email;
  if (identity && value.trim().toLowerCase() === identity.toLowerCase()) return "";
  return account.username ? "اسم المستخدم المدخل لا يطابق هذا الحساب." : "البريد الإلكتروني المدخل لا يطابق بريد المستخدم.";
}

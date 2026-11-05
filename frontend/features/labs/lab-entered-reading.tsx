import React from "react";
import type { LabResultResponse } from "@/lib/types";
import styles from "./labs.module.css";

export function LabEnteredReading({ result }: { result: LabResultResponse }) {
  if (result.entered_unit === result.display_unit) return null;
  return <span className={styles.enteredReading}>القيمة المُدخلة: <bdi dir="ltr">{result.entered_value} {result.entered_unit}</bdi></span>;
}

export function validateScore(value: string | number): { valid: boolean; value: number; error?: string } {
  const strVal = String(value).replace(",", ".");
  if (strVal.trim() === "") return { valid: true, value: 0 }; // empty means 0 for validation purposes unless required
  
  const num = parseFloat(strVal);
  if (isNaN(num)) {
    return { valid: false, value: 0, error: "Điểm không hợp lệ" };
  }
  
  if (num < 0 || num > 10) {
    return { valid: false, value: num, error: "Điểm phải từ 0 đến 10" };
  }
  
  return { valid: true, value: num };
}

export function validateIELTS(value: string | number): { valid: boolean; value: number; error?: string } {
  const strVal = String(value).replace(",", ".");
  if (strVal.trim() === "") return { valid: true, value: 0 };
  
  const num = parseFloat(strVal);
  if (isNaN(num)) {
    return { valid: false, value: 0, error: "Điểm không hợp lệ" };
  }
  
  if (num < 0 || num > 9) {
    return { valid: false, value: num, error: "Điểm IELTS phải từ 0 đến 9.0" };
  }
  
  if (num * 10 % 5 !== 0) {
    return { valid: false, value: num, error: "Điểm IELTS phải chia hết cho 0.5" };
  }
  
  return { valid: true, value: num };
}

export function validateMinSubjects(scores: Record<string, number | undefined>, minCount: number = 3): boolean {
  let count = 0;
  for (const subject in scores) {
    if (scores[subject] !== undefined && scores[subject] !== null && scores[subject] >= 0) {
      count++;
    }
  }
  return count >= minCount;
}

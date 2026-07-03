/**
 * Constants mapped from backend utils/score_calculator.py
 * Do not change unless backend is also updated.
 */

export const MAIN_SUBJECTS = [
  "Toán", "Ngữ văn", "Tiếng Anh",
  "Vật lý", "Hóa học", "Sinh học",
  "Lịch sử", "Địa lý", "GDCD",
] as const;

export const EXTRA_LANGUAGES = [
  "Tiếng Nhật", "Tiếng Trung", "Tiếng Pháp",
  "Tiếng Đức", "Tiếng Nga",
] as const;

export const EXTRA_APTITUDE = [
  "Vẽ", 
  "Năng khiếu Mầm non", 
  "Năng khiếu Âm nhạc", 
  "Năng khiếu TDTT", 
  "Năng khiếu SKĐA", 
  "Năng khiếu Báo chí"
] as const;

export const PRIORITY_KV: Record<string, number> = {
  "KV1": 0.75,
  "KV2-NT": 0.50,
  "KV2": 0.25,
  "KV3": 0.0,
};

export const PRIORITY_UT: Record<string, number> = {
  "Không": 0.0,
  "UT2": 1.0,
  "UT1": 2.0,
};

export const MIN_THRESHOLD = 15.0;
export const PRIORITY_REDUCTION_THRESHOLD = 22.5;

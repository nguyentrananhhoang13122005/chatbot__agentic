"use client";

import { useState } from "react";
import { MAIN_SUBJECTS } from "@/lib/constants";
import { ScoreInput } from "@/components/ui/score-input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScoreAction } from "@/hooks/use-score-form";

interface TranscriptEditorProps {
  dispatch: React.Dispatch<ScoreAction>;
}

// 9 Main subjects + Tin học, Công nghệ, GDQP
const ALL_SUBJECTS = [...MAIN_SUBJECTS, "Tin học", "Công nghệ", "GDQP-AN"];
const SEMESTERS = ["HK1 L10", "HK2 L10", "HK1 L11", "HK2 L11", "HK1 L12", "HK2 L12"];

export function TranscriptEditor({ dispatch }: TranscriptEditorProps) {
  const [formula, setFormula] = useState<"5HK" | "6HK" | "L12">("5HK");
  const [grid, setGrid] = useState<Record<string, Record<string, number | undefined>>>({});

  const handleScoreChange = (subject: string, semester: string, value: number | undefined) => {
    const newGrid = { ...grid };
    if (!newGrid[subject]) newGrid[subject] = {};
    newGrid[subject][semester] = value;
    setGrid(newGrid);
    updateAverage(subject, newGrid);
  };

  const updateAverage = (subject: string, currentGrid: typeof grid) => {
    const scores = currentGrid[subject] || {};
    let sum = 0;
    let count = 0;

    const semestersToCount = 
      formula === "5HK" ? SEMESTERS.slice(0, 5) :
      formula === "6HK" ? SEMESTERS :
      SEMESTERS.slice(4, 6);

    for (const sem of semestersToCount) {
      if (scores[sem] !== undefined) {
        sum += scores[sem]!;
        count++;
      }
    }

    if (count === semestersToCount.length) {
      // Calculate average
      const avg = Math.round((sum / count) * 100) / 100;
      dispatch({ type: "SET_SCORE", payload: { subject, value: avg } });
    } else {
      dispatch({ type: "SET_SCORE", payload: { subject, value: undefined } });
    }
  };

  const handleFormulaChange = (val: "5HK" | "6HK" | "L12") => {
    setFormula(val);
    ALL_SUBJECTS.forEach(subj => updateAverage(subj, grid));
  };

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between mb-4 bg-muted/30 p-4 rounded-xl border border-border">
        <div>
          <h3 className="font-medium text-foreground">Công thức xét Học bạ</h3>
          <p className="text-sm text-muted-foreground">Chọn công thức tính điểm trung bình (ĐTB) các môn học</p>
        </div>
        <Select value={formula} onValueChange={(val: any) => handleFormulaChange(val)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Chọn công thức" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="5HK">5 Học kỳ (L10, L11, HK1 L12)</SelectItem>
            <SelectItem value="6HK">6 Học kỳ (Cả L10, L11, L12)</SelectItem>
            <SelectItem value="L12">Cả năm Lớp 12 (2 Học kỳ)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-xl border border-border overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase bg-muted/50 text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium min-w-[120px] border-b border-border">Môn học</th>
              {SEMESTERS.map(sem => {
                // Highlight relevant columns based on formula
                const isRelevant = 
                  (formula === "5HK" && sem !== "HK2 L12") ||
                  (formula === "L12" && (sem === "HK1 L12" || sem === "HK2 L12")) ||
                  formula === "6HK";
                  
                return (
                  <th key={sem} className={`px-2 py-3 font-medium min-w-[80px] text-center border-b border-l border-border ${isRelevant ? 'text-primary' : ''}`}>
                    {sem}
                  </th>
                );
              })}
              <th className="px-4 py-3 font-medium min-w-[80px] text-center border-b border-l border-primary/30 bg-primary/5 text-primary">
                ĐTB
              </th>
            </tr>
          </thead>
          <tbody>
            {ALL_SUBJECTS.map((subject, idx) => {
              // Calculate preview average for display
              const scores = grid[subject] || {};
              let sum = 0; let count = 0;
              const semestersToCount = formula === "5HK" ? SEMESTERS.slice(0, 5) : formula === "6HK" ? SEMESTERS : SEMESTERS.slice(4, 6);
              semestersToCount.forEach(sem => {
                if (scores[sem] !== undefined) { sum += scores[sem]!; count++; }
              });
              const isComplete = count === semestersToCount.length && count > 0;
              const previewAvg = isComplete ? (sum / count).toFixed(2) : "-";

              return (
                <tr key={subject} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-2 font-medium">{subject}</td>
                  {SEMESTERS.map(sem => {
                     const isRelevant = 
                     (formula === "5HK" && sem !== "HK2 L12") ||
                     (formula === "L12" && (sem === "HK1 L12" || sem === "HK2 L12")) ||
                     formula === "6HK";
                    return (
                      <td key={`${subject}-${sem}`} className={`px-2 py-2 border-l border-border ${!isRelevant ? 'bg-muted/30 opacity-50' : ''}`}>
                        <ScoreInput
                          value={scores[sem]}
                          onChange={(val) => handleScoreChange(subject, sem, val)}
                          className="h-8 text-center px-1"
                          disabled={!isRelevant}
                        />
                      </td>
                    );
                  })}
                  <td className="px-4 py-2 text-center border-l border-primary/30 bg-primary/5 font-bold text-primary">
                    {previewAvg}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

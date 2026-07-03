import * as React from "react";
import { cn } from "@/lib/utils";
import { validateScore } from "@/lib/validators";

export interface ScoreInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  value: string | number | undefined;
  onChange: (val: number | undefined) => void;
  label?: string;
  error?: string;
  allowEmpty?: boolean;
}

export const ScoreInput = React.forwardRef<HTMLInputElement, ScoreInputProps>(
  ({ className, value, onChange, label, error: externalError, allowEmpty = true, ...props }, ref) => {
    const [localValue, setLocalValue] = React.useState<string>(value !== undefined ? String(value) : "");
    const [error, setError] = React.useState<string | undefined>(externalError);

    React.useEffect(() => {
      setLocalValue(value !== undefined ? String(value) : "");
    }, [value]);

    React.useEffect(() => {
      setError(externalError);
    }, [externalError]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setLocalValue(val);
      
      if (val.trim() === "" && allowEmpty) {
        setError(undefined);
        onChange(undefined);
        return;
      }

      const { valid, value: numValue, error: validationError } = validateScore(val);
      
      if (valid) {
        setError(undefined);
        onChange(numValue);
      } else {
        setError(validationError);
        // We don't propagate invalid values to parent, or we could. Parent should handle undefined.
        // Or if you prefer controlled form handling, parent just sees it's invalid.
      }
    };

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && <label className="text-sm font-medium text-foreground">{label}</label>}
        <input
          ref={ref}
          type="text"
          inputMode="decimal"
          className={cn(
            "flex h-10 w-full rounded-md border bg-background/50 px-3 py-2 text-sm",
            "ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium",
            "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            "disabled:cursor-not-allowed disabled:opacity-50 transition-colors",
            error ? "border-destructive focus-visible:ring-destructive" : "border-input",
            className
          )}
          value={localValue}
          onChange={handleChange}
          {...props}
        />
        {error && <span className="text-[0.8rem] text-destructive">{error}</span>}
      </div>
    );
  }
);
ScoreInput.displayName = "ScoreInput";

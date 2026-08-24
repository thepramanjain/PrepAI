import { type InputHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from "react";
import { twMerge } from "tailwind-merge";

const inputBase =
  "w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={twMerge(inputBase, "h-10", className)}
      {...props}
    />
  )
);
Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  resize?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, resize = false, ...props }, ref) => (
    <textarea
      ref={ref}
      className={twMerge(
        inputBase,
        "min-h-[100px] py-2.5",
        resize ? "resize-y" : "resize-none",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";

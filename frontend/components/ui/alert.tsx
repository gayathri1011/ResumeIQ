import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const alertVariants = cva(
  "rounded-[1.2rem] border p-4 text-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.65),0_12px_28px_-18px_rgba(55,38,18,0.28)]",
  {
    variants: {
      variant: {
        default: "border-border/70 bg-card text-foreground",
        success: "surface-success",
        warning: "surface-warning",
        info: "surface-info",
        error: "surface-error",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  title?: string;
}

export function Alert({
  className,
  variant = "default",
  title,
  children,
  ...props
}: AlertProps) {
  return (
    <div
      role="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    >
      <div className="min-w-0 space-y-1">
        {title ? <p className="font-medium leading-none">{title}</p> : null}
        <div className="text-muted-foreground [&_p]:leading-relaxed">
          {children}
        </div>
      </div>
    </div>
  );
}

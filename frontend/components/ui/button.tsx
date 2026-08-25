import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex touch-manipulation items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium tracking-wide transition-[transform,background-color,box-shadow,border-color,color,opacity] duration-100 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.97]",
  {
    variants: {
      variant: {
        default:
          "btn-3d bg-gradient-to-b from-primary/95 to-primary text-primary-foreground hover:from-primary hover:to-primary/90",
        destructive:
          "btn-3d bg-gradient-to-b from-destructive/95 to-destructive text-destructive-foreground",
        outline:
          "border border-border/80 bg-gradient-to-b from-card to-secondary/40 text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.7),0_8px_18px_-12px_rgba(55,38,18,0.35)] hover:border-primary/35",
        secondary:
          "border border-border/60 bg-gradient-to-b from-secondary to-secondary/80 text-secondary-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.65),0_6px_14px_-10px_rgba(55,38,18,0.3)]",
        ghost: "hover:bg-accent/70 hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        soft: "rounded-full border border-primary/25 bg-gradient-to-b from-card to-sand/50 text-foreground shadow-[inset_0_1px_0_rgba(255,255,255,0.8),0_8px_16px_-12px_rgba(55,38,18,0.35)] hover:border-primary/40",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-9 rounded-lg px-3.5 text-xs",
        lg: "h-12 rounded-2xl px-8 text-[0.95rem]",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };

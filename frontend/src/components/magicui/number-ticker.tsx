import { useEffect, useMemo, useRef, type ComponentPropsWithoutRef } from "react";
import { useInView, useMotionValue, useReducedMotion, useSpring } from "motion/react";
import { cn } from "@/lib/utils";

interface NumberTickerProps extends ComponentPropsWithoutRef<"span"> {
  value: number;
  decimalPlaces?: number;
}

// Magic UI Number Ticker, adapted for the Indonesian locale and reduced motion.
export function NumberTicker({ value, decimalPlaces = 0, className, ...props }: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reducedMotion = useReducedMotion();
  const target = useMotionValue(0);
  const spring = useSpring(target, { damping: 32, stiffness: 100 });
  const formatter = useMemo(() => new Intl.NumberFormat("id-ID", {
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  }), [decimalPlaces]);

  useEffect(() => {
    if (inView && !reducedMotion) target.set(value);
  }, [inView, reducedMotion, target, value]);

  useEffect(() => {
    if (reducedMotion) return;
    return spring.on("change", (latest) => {
      if (ref.current) ref.current.textContent = formatter.format(latest);
    });
  }, [formatter, reducedMotion, spring]);

  return <span ref={ref} className={cn("inline-block tabular-nums", className)} {...props}>
    {formatter.format(reducedMotion ? value : 0)}
  </span>;
}

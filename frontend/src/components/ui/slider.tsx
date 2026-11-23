import * as React from "react"
import { Slider as SliderPrimitive } from "radix-ui"

function Slider({
  "aria-label": ariaLabel,
  className,
  defaultValue,
  value,
  min = 0,
  max = 100,
  ...props
}: React.ComponentProps<typeof SliderPrimitive.Root>) {
  const _values = React.useMemo(
    () =>
      Array.isArray(value)
        ? value
        : Array.isArray(defaultValue)
          ? defaultValue
          : [min, max],
    [value, defaultValue, min, max]
  )

  return (
    <SliderPrimitive.Root
      data-slot="slider"
      aria-label={_values.length > 1 ? ariaLabel : undefined}
      defaultValue={defaultValue}
      value={value}
      min={min}
      max={max}
      className={className}
      {...props}
    >
      <SliderPrimitive.Track
        data-slot="slider-track"
        >
        <SliderPrimitive.Range
          data-slot="slider-range"
        />
      </SliderPrimitive.Track>
      {Array.from({ length: _values.length }, (_, index) => (
        <SliderPrimitive.Thumb
          data-slot="slider-thumb"
          aria-label={_values.length === 1 ? ariaLabel : undefined}
          key={index}
        />
      ))}
    </SliderPrimitive.Root>
  )
}

export { Slider }

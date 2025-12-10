import { cn } from '@workspace/ui/lib/utils';

const PRESET_COLORS = [
  '#6366F1', // Indigo
  '#EF4444', // Red
  '#22C55E', // Green
  '#3B82F6', // Blue
  '#F59E0B', // Amber
  '#EC4899', // Pink
  '#8B5CF6', // Violet
  '#14B8A6', // Teal
] as const;

interface ColorPickerProps {
  value: string;
  onChange: (color: string) => void;
  className?: string;
}

function ColorPicker({ value, onChange, className }: ColorPickerProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex gap-1">
        {PRESET_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            onClick={() => onChange(color)}
            className={cn(
              'h-6 w-6 rounded-md border-2 transition-transform hover:scale-110',
              value === color ? 'border-foreground' : 'border-transparent',
            )}
            style={{ backgroundColor: color }}
            title={color}
          />
        ))}
      </div>
      <div className="relative">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        />
        <div
          className="border-input h-6 w-6 rounded-md border"
          style={{ backgroundColor: value }}
        />
      </div>
    </div>
  );
}

export { ColorPicker, PRESET_COLORS };

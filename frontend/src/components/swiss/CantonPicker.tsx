'use client';
import { CANTONS_ROMANDS, CANTONS_AUTRES } from '@/lib/ch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface Props {
  value: string;
  onChange: (canton: string) => void;
  placeholder?: string;
  includeAll?: boolean;
}

export function CantonPicker({ value, onChange, placeholder = 'Sélectionner un canton', includeAll = true }: Props) {
  return (
    <Select value={value || ''} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">Suisse romande</div>
        {CANTONS_ROMANDS.map((c) => (
          <SelectItem key={c.code} value={c.code}>{c.name} ({c.code})</SelectItem>
        ))}
        {includeAll && (
          <>
            <div className="px-2 py-1.5 mt-2 text-xs font-semibold text-muted-foreground">Autres cantons</div>
            {CANTONS_AUTRES.map((c) => (
              <SelectItem key={c.code} value={c.code}>{c.name} ({c.code})</SelectItem>
            ))}
          </>
        )}
      </SelectContent>
    </Select>
  );
}

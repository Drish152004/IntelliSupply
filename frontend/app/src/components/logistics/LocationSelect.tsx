import { ChevronDown } from 'lucide-react';
import { Label } from '@/components/ui/label';
import type { CityListItem, HubListItem } from '@/lib/api';

const selectClassName =
  'w-full appearance-none rounded-lg border border-border bg-white py-2 pl-3 pr-8 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-60';

interface CitySelectProps {
  label: string;
  value: string;
  onChange: (cityName: string) => void;
  cities: CityListItem[];
  disabled?: boolean;
  placeholder?: string;
}

export function CitySelect({
  label,
  value,
  onChange,
  cities,
  disabled,
  placeholder = 'Select city',
}: CitySelectProps) {
  return (
    <div>
      <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</Label>
      <div className="relative mt-2">
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={selectClassName}
        >
          <option value="">{placeholder}</option>
          {cities.map((city) => (
            <option key={city.city_id ?? city.city_name} value={city.city_name}>
              {city.city_name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

interface HubSelectProps {
  label: string;
  value: string;
  onChange: (hubName: string) => void;
  hubs: HubListItem[];
  disabled?: boolean;
  placeholder?: string;
}

export function HubSelect({
  label,
  value,
  onChange,
  hubs,
  disabled,
  placeholder = 'Select hub',
}: HubSelectProps) {
  return (
    <div>
      <Label className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</Label>
      <div className="relative mt-2">
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={selectClassName}
        >
          <option value="">{placeholder}</option>
          {hubs.map((hub) => (
            <option key={hub.hub_id ?? hub.hub_name} value={hub.hub_name}>
              {hub.hub_name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

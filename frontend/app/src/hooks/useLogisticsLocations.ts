import { useEffect, useState } from 'react';
import {
  listCities,
  listHubs,
  type CityListItem,
  type HubListItem,
} from '@/lib/api';

export function useLogisticsLocations(cityName?: string) {
  const [cities, setCities] = useState<CityListItem[]>([]);
  const [hubs, setHubs] = useState<HubListItem[]>([]);
  const [loadingCities, setLoadingCities] = useState(false);
  const [loadingHubs, setLoadingHubs] = useState(false);

  useEffect(() => {
    setLoadingCities(true);

    void listCities()
      .then(setCities)
      .catch(() => setCities([]))
      .finally(() => setLoadingCities(false));
  }, []);

  useEffect(() => {
    setLoadingHubs(true);

    /*
      Empty cityName means fetch all hubs.
      This is needed for the logistics China map.
    */
    void listHubs(cityName ?? '')
      .then(setHubs)
      .catch(() => setHubs([]))
      .finally(() => setLoadingHubs(false));
  }, [cityName]);

  return {
    cities,
    hubs,
    loadingCities,
    loadingHubs,
  };
}
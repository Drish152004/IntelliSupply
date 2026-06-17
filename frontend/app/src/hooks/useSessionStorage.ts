import { useState, useEffect, type Dispatch, type SetStateAction } from 'react';

export function useSessionStorageState<T>(key: string, defaultValue: T): [T, Dispatch<SetStateAction<T>>] {
  const [state, setState] = useState<T>(() => {
    try {
      const item = sessionStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  });

  const [prevKey, setPrevKey] = useState(key);

  if (key !== prevKey) {
    setPrevKey(key);
    try {
      const item = sessionStorage.getItem(key);
      setState(item ? JSON.parse(item) : defaultValue);
    } catch {
      setState(defaultValue);
    }
  }

  useEffect(() => {
    try {
      if (state === undefined) {
        sessionStorage.removeItem(key);
      } else {
        sessionStorage.setItem(key, JSON.stringify(state));
      }
    } catch (error) {
      console.error(`Error writing sessionStorage key "${key}":`, error);
    }
  }, [key, state]);

  return [state, setState];
}

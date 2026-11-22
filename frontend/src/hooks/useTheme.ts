import { useEffect, useState } from 'react';

export function useTheme() {
  const [dark, setDark] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    const saved = window.localStorage.getItem('baap_theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
      window.localStorage.setItem('baap_theme', 'dark');
    } else {
      root.classList.remove('dark');
      window.localStorage.setItem('baap_theme', 'light');
    }
  }, [dark]);

  return { dark, toggleTheme: () => setDark((prev) => !prev) };
}

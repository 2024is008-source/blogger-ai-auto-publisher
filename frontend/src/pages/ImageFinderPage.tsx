import React, { useState } from 'react';
import { ExternalLink, Loader2, PlusCircle, Search, ShieldCheck } from 'lucide-react';
import type { ImageAsset, LicenseFilter } from '../types';
import { searchPublicImages } from '../services/githubApi';

interface ImageFinderPageProps {
  defaultFilter: LicenseFilter;
  savedLicenses: ImageAsset[];
  onInsertImage: (asset: ImageAsset) => void;
  onNotify: (type: 'success' | 'error' | 'info', title: string, detail?: string) => void;
}

export const ImageFinderPage: React.FC<ImageFinderPageProps> = ({
  defaultFilter,
  savedLicenses,
  onInsertImage,
  onNotify,
}) => {
  const [query, setQuery] = useState('');
  const [licenseFilter, setLicenseFilter] = useState<LicenseFilter>(defaultFilter);
  const [results, setResults] = useState<ImageAsset[]>([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const found = await searchPublicImages(query.trim(), licenseFilter);
      setResults(found);
      if (found.length === 0) {
        onNotify('info', 'No matching licensed images found', 'Try broader keywords or relax the license filter.');
      }
    } catch (err) {
      onNotify('error', 'Image search failed', err instanceof Error ? err.message : 'Network error');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSearch}
        className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
              Copyright-Permitted Image Finder
            </h2>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Live browser search queries Openverse and Wikimedia Commons with individual asset-level license verification. Pexels &amp; Pixabay run via GitHub Actions to keep API keys inside GitHub Secrets.
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search descriptive visual terms (e.g., workspace laptop desk)..."
            className="h-10 flex-1 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          />
          <select
            aria-label="License filter"
            value={licenseFilter}
            onChange={(e) => setLicenseFilter(e.target.value as LicenseFilter)}
            className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
          >
            <option value="cc0_public_domain">CC0 / Public Domain only</option>
            <option value="commercial_permitted">Commercial-use permitted</option>
            <option value="cc_with_attribution">Creative Commons with attribution</option>
            <option value="all_supported">All supported licenses</option>
          </select>
          <button
            type="submit"
            disabled={searching || !query.trim()}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {searching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </button>
        </div>
      </form>

      {/* Live Search Results */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {results.map((img) => (
            <article
              key={`${img.source_provider}-${img.id}`}
              className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="aspect-video w-full overflow-hidden bg-slate-100 dark:bg-slate-800">
                <img
                  src={img.preview_url}
                  alt={img.alt_text || img.title}
                  loading="lazy"
                  className="h-full w-full object-cover"
                />
              </div>
              <div className="flex flex-1 flex-col p-4">
                <h3 className="line-clamp-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {img.title}
                </h3>
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  Creator: {img.creator_name} · {img.source_provider}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                  <span className="inline-flex items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300">
                    <ShieldCheck className="h-3 w-3" />
                    {img.license_name}
                  </span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {img.attribution_required ? 'Attribution required' : 'No attribution required'}
                  </span>
                </div>
                <div className="mt-auto flex items-center justify-between gap-2 pt-4">
                  <a
                    href={img.license_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline"
                  >
                    License <ExternalLink className="h-3 w-3" />
                  </a>
                  <button
                    type="button"
                    onClick={() => onInsertImage(img)}
                    className="inline-flex items-center gap-1 rounded-lg bg-navy-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 dark:bg-brand-600 dark:hover:bg-brand-700"
                  >
                    <PlusCircle className="h-3.5 w-3.5" /> Insert into Editor
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Recorded License Registry */}
      <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Stored Image License Registry ({savedLicenses.length})
        </h3>
        {savedLicenses.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            No image licenses recorded in data/image-licenses/licenses.json yet.
          </p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-200 uppercase text-slate-500 dark:border-slate-800">
                  <th className="py-2 pr-3">Title</th>
                  <th className="py-2 pr-3">Provider</th>
                  <th className="py-2 pr-3">Creator</th>
                  <th className="py-2 pr-3">License</th>
                  <th className="py-2">Retrieved</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {savedLicenses.map((lic) => (
                  <tr key={`${lic.source_provider}-${lic.id}`}>
                    <td className="py-2 pr-3 font-medium">{lic.title}</td>
                    <td className="py-2 pr-3">{lic.source_provider}</td>
                    <td className="py-2 pr-3">{lic.creator_name}</td>
                    <td className="py-2 pr-3">
                      <a href={lic.license_url} target="_blank" rel="noopener noreferrer" className="text-brand-600 hover:underline">
                        {lic.license_name}
                      </a>
                    </td>
                    <td className="py-2 tabular-nums text-slate-500">{lic.retrieval_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

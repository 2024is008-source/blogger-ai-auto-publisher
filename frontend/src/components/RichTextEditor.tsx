import React, { useEffect, useRef, useState } from 'react';
import {
  Bold,
  Code2,
  Copy,
  Eye,
  Heading2,
  Heading3,
  Image as ImageIcon,
  Italic,
  Link2,
  List,
  ListOrdered,
  RefreshCw,
  Table,
  Type,
} from 'lucide-react';

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  onCopyHtml: () => void;
  onRegenerateParagraph?: (selectedText: string) => void;
  onOpenImagePicker?: () => void;
}

type EditorMode = 'visual' | 'source' | 'preview';

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  onCopyHtml,
  onRegenerateParagraph,
  onOpenImagePicker,
}) => {
  const [mode, setMode] = useState<EditorMode>('visual');
  const [imageWidth, setImageWidth] = useState<string>('100%');
  const visualRef = useRef<HTMLDivElement | null>(null);

  // Sync incoming HTML into contentEditable only when entering visual mode or when value changes externally
  useEffect(() => {
    if (mode === 'visual' && visualRef.current && visualRef.current.innerHTML !== value) {
      visualRef.current.innerHTML = value;
    }
  }, [mode, value]);

  const handleModeChange = (next: EditorMode) => {
    if (mode === 'visual' && visualRef.current) {
      onChange(visualRef.current.innerHTML);
    }
    setMode(next);
  };

  const exec = (command: string, arg?: string) => {
    if (mode !== 'visual') return;
    visualRef.current?.focus();
    document.execCommand(command, false, arg);
    if (visualRef.current) {
      onChange(visualRef.current.innerHTML);
    }
  };

  const insertHtmlSnippet = (snippet: string) => {
    if (mode === 'visual' && visualRef.current) {
      visualRef.current.focus();
      document.execCommand('insertHTML', false, snippet);
      onChange(visualRef.current.innerHTML);
    } else {
      onChange(`${value}\n${snippet}`);
    }
  };

  const handleInsertLink = () => {
    const url = window.prompt('Enter destination URL (https://...)');
    if (!url || !/^https?:\/\//i.test(url.trim())) return;
    exec('createLink', url.trim());
  };

  const handleInsertTable = () => {
    insertHtmlSnippet(
      `<table><thead><tr><th>Feature</th><th>Option A</th><th>Option B</th></tr></thead><tbody><tr><td>Summary</td><td>Detail A</td><td>Detail B</td></tr></tbody></table>`
    );
  };

  const handleResizeImages = (widthVal: string) => {
    setImageWidth(widthVal);
    const parser = new DOMParser();
    const doc = parser.parseFromString(value || '', 'text/html');
    doc.querySelectorAll('img').forEach((img) => {
      img.style.width = widthVal;
      img.style.maxWidth = '100%';
      img.style.height = 'auto';
    });
    const updated = doc.body.innerHTML;
    onChange(updated);
    if (visualRef.current) visualRef.current.innerHTML = updated;
  };

  const handleRegenerateSelection = () => {
    const sel = window.getSelection()?.toString().trim() || '';
    if (onRegenerateParagraph) {
      onRegenerateParagraph(sel);
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      {/* Mode Switcher + Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-800 dark:bg-slate-900/80">
        <div className="flex flex-wrap items-center gap-1">
          <button
            type="button"
            onClick={() => exec('formatBlock', 'h2')}
            disabled={mode !== 'visual'}
            title="Heading 2"
            aria-label="Insert Heading 2"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Heading2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => exec('formatBlock', 'h3')}
            disabled={mode !== 'visual'}
            title="Heading 3"
            aria-label="Insert Heading 3"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Heading3 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => exec('bold')}
            disabled={mode !== 'visual'}
            title="Bold"
            aria-label="Bold"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Bold className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => exec('italic')}
            disabled={mode !== 'visual'}
            title="Italic"
            aria-label="Italic"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Italic className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => exec('insertUnorderedList')}
            disabled={mode !== 'visual'}
            title="Bulleted list"
            aria-label="Bulleted list"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <List className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => exec('insertOrderedList')}
            disabled={mode !== 'visual'}
            title="Numbered list"
            aria-label="Numbered list"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <ListOrdered className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleInsertLink}
            disabled={mode !== 'visual'}
            title="Insert link"
            aria-label="Insert link"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Link2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleInsertTable}
            title="Insert HTML table"
            aria-label="Insert HTML table"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <Table className="h-4 w-4" />
          </button>
          {onOpenImagePicker && (
            <button
              type="button"
              onClick={onOpenImagePicker}
              title="Insert licensed image"
              aria-label="Insert licensed image"
              className="rounded-md p-1.5 text-slate-600 hover:bg-slate-200/70 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <ImageIcon className="h-4 w-4" />
            </button>
          )}
          <select
            aria-label="Resize embedded images"
            value={imageWidth}
            onChange={(e) => handleResizeImages(e.target.value)}
            className="ml-1 h-7 rounded-md border border-slate-300 bg-white px-2 text-xs text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="100%">Img 100%</option>
            <option value="75%">Img 75%</option>
            <option value="50%">Img 50%</option>
          </select>
          {onRegenerateParagraph && (
            <button
              type="button"
              onClick={handleRegenerateSelection}
              className="ml-1 inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Regenerate Selection
            </button>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-800">
            <button
              type="button"
              onClick={() => handleModeChange('visual')}
              className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                mode === 'visual'
                  ? 'bg-navy-900 text-white dark:bg-brand-600'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300'
              }`}
            >
              <Type className="h-3.5 w-3.5" /> Visual
            </button>
            <button
              type="button"
              onClick={() => handleModeChange('source')}
              className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                mode === 'source'
                  ? 'bg-navy-900 text-white dark:bg-brand-600'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300'
              }`}
            >
              <Code2 className="h-3.5 w-3.5" /> HTML
            </button>
            <button
              type="button"
              onClick={() => handleModeChange('preview')}
              className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium ${
                mode === 'preview'
                  ? 'bg-navy-900 text-white dark:bg-brand-600'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300'
              }`}
            >
              <Eye className="h-3.5 w-3.5" /> Preview
            </button>
          </div>

          <button
            type="button"
            onClick={onCopyHtml}
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <Copy className="h-3.5 w-3.5" /> Copy HTML
          </button>
        </div>
      </div>

      {/* Editor Body */}
      {mode === 'visual' && (
        <div
          ref={visualRef}
          contentEditable
          suppressContentEditableWarning
          onInput={(e) => onChange(e.currentTarget.innerHTML)}
          aria-label="Rich text article editor"
          className="article-preview min-h-[380px] p-5 text-sm focus:outline-none"
        />
      )}

      {mode === 'source' && (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-label="HTML source editor"
          spellCheck={false}
          className="min-h-[380px] w-full resize-y bg-slate-950 p-4 font-mono text-xs leading-relaxed text-emerald-300 focus:outline-none"
        />
      )}

      {mode === 'preview' && (
        <div
          className="article-preview min-h-[380px] p-6"
          dangerouslySetInnerHTML={{ __html: value || '<p>No article content yet.</p>' }}
        />
      )}
    </div>
  );
};

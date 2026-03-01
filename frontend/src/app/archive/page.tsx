"use client";
import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { docsApi } from "@/lib/api";
import toast from "react-hot-toast";
import { clsx } from "clsx";

interface Doc {
  id: string;
  filename: string;
  lab_name: string;
  doc_date: string | null;
  uploaded_at: string;
  status: string;
  source: string;
}

export default function ArchivePage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchDocs = (q?: string) => {
    setLoading(true);
    docsApi.list(q).then((r) => setDocs(r.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); fetchDocs(search); };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await docsApi.upload(file);
      toast.success("Загружено! Идёт обработка AI-Shield...");
      fetchDocs();
    } catch { toast.error("Ошибка загрузки"); }
    finally { setUploading(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить документ?")) return;
    try {
      await docsApi.delete(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      toast.success("Удалено");
    } catch { toast.error("Ошибка"); }
  };

  const handleDownload = async (id: string, filename: string) => {
    try {
      const res = await docsApi.download(id);
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
    } catch { toast.error("Ошибка скачивания"); }
  };

  return (
    <AppLayout>
      <div className="space-y-5">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Архив документов</h1>
          <label className="btn-primary text-sm cursor-pointer">
            <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={handleUpload} />
            {uploading ? "..." : "+ Добавить"}
          </label>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Поиск по названию или лаборатории..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn-secondary">Найти</button>
        </form>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent" />
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <div className="text-4xl mb-2">📂</div>
            <p>Документы не найдены</p>
          </div>
        ) : (
          <div className="space-y-3">
            {docs.map((d) => (
              <div key={d.id} className="card flex items-center gap-3">
                <div className="text-2xl">{d.filename?.endsWith(".pdf") ? "📄" : "🖼"}</div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{d.filename}</p>
                  <p className="text-xs text-gray-400">
                    {d.lab_name || "Лаборатория"} ·{" "}
                    {(d.doc_date || d.uploaded_at).slice(0, 10)} ·{" "}
                    {d.source === "email_sync" ? "📧 Email" : "📱 Ручная"}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={clsx("text-xs px-2 py-0.5 rounded-full",
                    d.status === "done" ? "bg-green-50 text-green-700" :
                    d.status === "error" ? "bg-red-50 text-red-700" : "bg-yellow-50 text-yellow-700"
                  )}>
                    {d.status === "done" ? "✓" : d.status === "error" ? "✗" : "⏳"}
                  </span>
                  <button
                    onClick={() => handleDownload(d.id, d.filename)}
                    className="text-brand-500 hover:text-brand-700 text-lg"
                    title="Скачать"
                  >⬇</button>
                  <button
                    onClick={() => handleDelete(d.id)}
                    className="text-red-400 hover:text-red-600 text-lg"
                    title="Удалить"
                  >🗑</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}

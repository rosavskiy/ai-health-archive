"use client";
import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { metricsApi, docsApi } from "@/lib/api";
import { clsx } from "clsx";
import toast from "react-hot-toast";
import Link from "next/link";

interface MetricSummary {
  name: string;
  value: number;
  unit: string;
  is_abnormal: boolean;
  measured_at: string;
  reference_min: number | null;
  reference_max: number | null;
}

interface Doc {
  id: string;
  filename: string;
  lab_name: string;
  doc_date: string | null;
  uploaded_at: string;
  status: string;
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<MetricSummary[]>([]);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    metricsApi.summary().then((r) => setMetrics(r.data)).catch(() => {});
    docsApi.list().then((r) => setDocs(r.data.slice(0, 5))).catch(() => {});
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await docsApi.upload(file);
      toast.success("Файл загружен! Идёт AI-обработка...");
      const r = await docsApi.list();
      setDocs(r.data.slice(0, 5));
    } catch {
      toast.error("Ошибка загрузки файла");
    } finally {
      setUploading(false);
    }
  };

  const abnormal = metrics.filter((m) => m.is_abnormal);

  return (
    <AppLayout>
      <div className="space-y-5">
        {/* Welcome */}
        <div>
          <h1 className="text-2xl font-bold">Мой дашборд</h1>
          <p className="text-gray-500 text-sm mt-0.5">Сводка по вашему здоровью</p>
        </div>

        {/* Upload CTA */}
        <label className="block card border-2 border-dashed border-brand-200 cursor-pointer hover:border-brand-400 transition-colors text-center py-6">
          <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={handleFileUpload} />
          <div className="text-3xl mb-2">📄</div>
          <p className="font-semibold text-brand-700">{uploading ? "Загружаем..." : "Добавить анализ"}</p>
          <p className="text-sm text-gray-500 mt-0.5">PDF или фото (JPG/PNG)</p>
        </label>

        {/* Abnormal alerts */}
        {abnormal.length > 0 && (
          <div className="card border-red-200 bg-red-50 space-y-2">
            <p className="font-semibold text-red-700 flex items-center gap-1">⚠ Отклонения от нормы</p>
            {abnormal.map((m) => (
              <div key={m.name} className="flex justify-between text-sm">
                <span className="text-gray-700">{m.name}</span>
                <span className="font-semibold text-red-600">
                  {m.value} {m.unit}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Metrics grid */}
        {metrics.length > 0 && (
          <div>
            <h2 className="font-semibold text-gray-700 mb-3">Последние показатели</h2>
            <div className="grid grid-cols-2 gap-3">
              {metrics.slice(0, 6).map((m) => (
                <div key={m.name} className="card space-y-1">
                  <p className="text-xs text-gray-400">{m.name}</p>
                  <p className={clsx("text-xl font-bold", m.is_abnormal ? "text-red-600" : "text-green-600")}>
                    {m.value} <span className="text-xs font-normal text-gray-400">{m.unit}</span>
                  </p>
                  <span className={m.is_abnormal ? "badge-warn" : "badge-ok"}>
                    {m.is_abnormal ? "Отклонение" : "Норма"}
                  </span>
                </div>
              ))}
            </div>
            <Link href="/trends" className="text-sm text-brand-600 mt-3 inline-block hover:underline">
              Посмотреть динамику →
            </Link>
          </div>
        )}

        {/* Recent docs */}
        {docs.length > 0 && (
          <div>
            <h2 className="font-semibold text-gray-700 mb-3">Последние документы</h2>
            <div className="space-y-2">
              {docs.map((d) => (
                <div key={d.id} className="card flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium truncate max-w-[180px]">{d.filename}</p>
                    <p className="text-xs text-gray-400">{d.lab_name || "Лаборатория"} · {d.doc_date?.slice(0, 10) || d.uploaded_at.slice(0, 10)}</p>
                  </div>
                  <span className={clsx("text-xs px-2 py-0.5 rounded-full",
                    d.status === "done" ? "bg-green-50 text-green-700" :
                    d.status === "error" ? "bg-red-50 text-red-700" :
                    "bg-yellow-50 text-yellow-700"
                  )}>
                    {d.status === "done" ? "Готово" : d.status === "error" ? "Ошибка" : "Обработка..."}
                  </span>
                </div>
              ))}
            </div>
            <Link href="/archive" className="text-sm text-brand-600 mt-3 inline-block hover:underline">
              Весь архив →
            </Link>
          </div>
        )}

        {metrics.length === 0 && docs.length === 0 && !uploading && (
          <div className="text-center py-12 text-gray-400">
            <div className="text-5xl mb-3">🧪</div>
            <p>Загрузите первый анализ, чтобы начать</p>
          </div>
        )}
      </div>
    </AppLayout>
  );
}

"use client";
import { useEffect, useState } from "react";
import AppLayout from "@/components/AppLayout";
import { metricsApi } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

interface TrendData {
  name: string;
  unit: string;
  reference_min: number | null;
  reference_max: number | null;
  data: { date: string; value: number }[];
}

export default function TrendsPage() {
  const [names, setNames] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [trend, setTrend] = useState<TrendData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    metricsApi.names().then((r) => {
      setNames(r.data);
      if (r.data.length) setSelected(r.data[0]);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    metricsApi.trend(selected)
      .then((r) => setTrend(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selected]);

  const chartData = trend
    ? {
        labels: trend.data.map((d) => d.date.slice(0, 10)),
        datasets: [
          {
            label: `${trend.name} (${trend.unit})`,
            data: trend.data.map((d) => d.value),
            borderColor: "#0ea5e9",
            backgroundColor: "rgba(14,165,233,0.08)",
            fill: true,
            tension: 0.4,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
          ...(trend.reference_min != null && trend.reference_max != null
            ? [
                {
                  label: "Верхняя граница нормы",
                  data: trend.data.map(() => trend.reference_max!),
                  borderColor: "#f97316",
                  borderDash: [5, 5],
                  fill: false,
                  pointRadius: 0,
                  borderWidth: 1,
                },
                {
                  label: "Нижняя граница нормы",
                  data: trend.data.map(() => trend.reference_min!),
                  borderColor: "#22c55e",
                  borderDash: [5, 5],
                  fill: false,
                  pointRadius: 0,
                  borderWidth: 1,
                },
              ]
            : []),
        ],
      }
    : null;

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { position: "bottom" as const },
      title: { display: false },
    },
    scales: {
      y: { beginAtZero: false },
    },
  };

  return (
    <AppLayout>
      <div className="space-y-5">
        <h1 className="text-2xl font-bold">Динамика показателей</h1>

        {names.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <div className="text-4xl mb-2">📈</div>
            <p>Загрузите анализы для просмотра динамики</p>
          </div>
        ) : (
          <>
            {/* Selector */}
            <div className="flex flex-wrap gap-2">
              {names.map((name) => (
                <button
                  key={name}
                  onClick={() => setSelected(name)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    selected === name
                      ? "bg-brand-500 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {name}
                </button>
              ))}
            </div>

            {/* Chart */}
            <div className="card">
              {loading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-brand-500 border-t-transparent" />
                </div>
              ) : chartData ? (
                <>
                  <h2 className="font-semibold mb-4">{selected}</h2>
                  <Line data={chartData} options={chartOptions} />
                  {trend && (
                    <div className="mt-4 grid grid-cols-2 gap-3">
                      {trend.data.slice(-3).reverse().map((d) => (
                        <div key={d.date} className="bg-gray-50 rounded-xl p-3">
                          <p className="text-xs text-gray-400">{d.date.slice(0, 10)}</p>
                          <p className="text-lg font-bold text-brand-700">
                            {d.value} <span className="text-sm font-normal text-gray-400">{trend.unit}</span>
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}

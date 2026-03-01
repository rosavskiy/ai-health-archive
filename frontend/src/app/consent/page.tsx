"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ConsentPage() {
  const router = useRouter();
  const [checked1, setChecked1] = useState(false);
  const [checked2, setChecked2] = useState(false);
  const [checked3, setChecked3] = useState(false);

  const allChecked = checked1 && checked2 && checked3;

  const handleAccept = () => {
    localStorage.setItem("consent_accepted", "true");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 to-white flex items-center justify-center p-4">
      <div className="card max-w-lg w-full space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="text-4xl">🏥</div>
          <h1 className="text-2xl font-bold text-brand-900">AI Health Archive</h1>
          <p className="text-gray-500 text-sm">
            Персональный архив медицинских анализов с AI-консультантом
          </p>
        </div>

        {/* Legal notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800 space-y-1">
          <p className="font-semibold">Соответствие 152-ФЗ РФ</p>
          <p>
            Все ваши данные хранятся исключительно на серверах в Российской Федерации.
            Перед передачей на AI-обработку документы автоматически деперсонализируются.
          </p>
        </div>

        {/* Checkboxes */}
        <div className="space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5 h-5 w-5 rounded accent-brand-500"
              checked={checked1}
              onChange={(e) => setChecked1(e.target.checked)}
            />
            <span className="text-sm text-gray-700">
              Я прочитал(а) и принимаю{" "}
              <a href="/docs/offer.pdf" className="text-brand-600 underline" target="_blank">
                Публичную оферту
              </a>{" "}
              и{" "}
              <a href="/docs/privacy.pdf" className="text-brand-600 underline" target="_blank">
                Политику конфиденциальности
              </a>
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5 h-5 w-5 rounded accent-brand-500"
              checked={checked2}
              onChange={(e) => setChecked2(e.target.checked)}
            />
            <span className="text-sm text-gray-700">
              Я даю согласие на обработку специальных категорий персональных данных
              (медицинских сведений) в соответствии со ст. 10 Федерального закона № 152-ФЗ
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              className="mt-0.5 h-5 w-5 rounded accent-brand-500"
              checked={checked3}
              onChange={(e) => setChecked3(e.target.checked)}
            />
            <span className="text-sm text-gray-700">
              Я понимаю, что персональные данные будут деперсонализированы перед
              AI-обработкой, и согласен(на) на обезличивание медицинских документов
            </span>
          </label>
        </div>

        <button
          onClick={handleAccept}
          disabled={!allChecked}
          className="btn-primary w-full text-center"
        >
          Принять и продолжить
        </button>

        <p className="text-xs text-center text-gray-400">
          Версия 5.0 · AI Health Archive © 2026
        </p>
      </div>
    </div>
  );
}

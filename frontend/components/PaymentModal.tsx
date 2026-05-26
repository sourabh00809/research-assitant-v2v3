"use client";

import { useState } from "react";

interface PaymentModalProps {
  tier: string;
  price: string;
  name: string;
  onSuccess: () => void;
  onCancel: () => void;
}

export function PaymentModal({ tier, price, name, onSuccess, onCancel }: PaymentModalProps) {
  const [step, setStep] = useState<"form" | "processing" | "success">("form");
  const [cardNumber, setCardNumber] = useState("4242 4242 4242 4242");
  const [expiry, setExpiry] = useState("12/28");
  const [cvv, setCvv] = useState("123");
  const [cardName, setCardName] = useState("Test User");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStep("processing");
    setTimeout(() => setStep("success"), 1800);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white shadow-xl">
        {step === "form" && (
          <form onSubmit={handleSubmit}>
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="text-lg font-bold">Upgrade to {name}</h2>
              <p className="text-sm text-slate-600">{price} — billed monthly</p>
            </div>
            <div className="space-y-4 px-6 py-4">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Cardholder Name</label>
                <input
                  className="w-full rounded-md border border-slate-300 p-2 text-sm"
                  value={cardName}
                  onChange={(e) => setCardName(e.target.value)}
                  placeholder="John Doe"
                  required
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">Card Number</label>
                <input
                  className="w-full rounded-md border border-slate-300 p-2 text-sm font-mono"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  placeholder="4242 4242 4242 4242"
                  maxLength={19}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">Expiry</label>
                  <input
                    className="w-full rounded-md border border-slate-300 p-2 text-sm font-mono"
                    value={expiry}
                    onChange={(e) => setExpiry(e.target.value)}
                    placeholder="MM/YY"
                    maxLength={5}
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-600">CVV</label>
                  <input
                    className="w-full rounded-md border border-slate-300 p-2 text-sm font-mono"
                    value={cvv}
                    onChange={(e) => setCvv(e.target.value)}
                    placeholder="123"
                    maxLength={4}
                    required
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
              <button
                type="button"
                onClick={onCancel}
                className="rounded-md px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded-md bg-emerald-700 px-6 py-2 text-sm font-bold text-white hover:bg-emerald-800"
              >
                Pay {price}
              </button>
            </div>
          </form>
        )}

        {step === "processing" && (
          <div className="flex flex-col items-center px-6 py-12">
            <div className="mb-4 h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-emerald-700" />
            <p className="text-sm font-semibold text-slate-700">Processing payment...</p>
            <p className="mt-1 text-xs text-slate-500">Please do not close this window</p>
          </div>
        )}

        {step === "success" && (
          <div className="flex flex-col items-center px-6 py-12">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100">
              <svg className="h-7 w-7 text-emerald-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-lg font-bold text-emerald-800">Payment Successful!</p>
            <p className="mt-1 text-sm text-slate-600">You are now on the <strong>{name}</strong> plan.</p>
            <button
              onClick={onSuccess}
              className="mt-6 rounded-md bg-emerald-700 px-6 py-2 text-sm font-bold text-white hover:bg-emerald-800"
            >
              Continue
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

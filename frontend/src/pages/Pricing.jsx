import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";
import { useNavigate } from "react-router-dom";
import { Loader2, TrendingUp, DollarSign, ArrowRight } from "lucide-react";

export default function Pricing() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    const poll = setInterval(async () => {
      if (!threadId) return;

      const res = await getWorkflowState(threadId);
      setState(res.data);

     if (res.data?.pricing_detailed.summary || res.data?.status === "completed") {
        setIsLoading(false);
        clearInterval(poll);
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [threadId]);

  if (isLoading || !state?.pricing_detailed) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="card p-12 text-center">
          <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={32} />
          <h2 className="text-xl font-semibold">Calculating pricing...</h2>
          <p className="text-slate-400 mt-2">Analyzing product specifications and market rates</p>
        </div>
      </div>
    );
  }

  const s = state.pricing_detailed.summary;

  const formatCurrency = (value) => {
    if (value === undefined || value === null || isNaN(value)) return '0.00';
    return value.toLocaleString('en-IN', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    });
  };

  const pricingItems = [
    { label: 'Total Material', value: s.total_material_cost_inr, icon: '📦' },
    { label: 'Total Testing', value: s.total_testing_cost_inr, icon: '🧪' },
    { label: 'Subtotal', value: s.subtotal_inr, icon: '📋', highlight: true },
    { label: 'Contingency (10%)', value: s.contingency_10pct_inr, icon: '⚠️', highlight: true },
  ];

  return (
    <div className="min-h-screen gradient-bg py-12">
      <div className="max-w-4xl mx-auto px-6">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-gradient-to-r from-amber-500 to-orange-500 rounded-lg">
              <TrendingUp size={24} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold">Pricing Summary</h1>
          </div>
          <p className="text-slate-400 text-lg">Detailed cost breakdown for your RFP response</p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {pricingItems.map((item, idx) => (
            <div 
              key={idx} 
              className={`card p-6 flex items-center justify-between ${
                item.highlight ? 'bg-gradient-to-r from-slate-800 to-slate-900 border-cyan-500/30' : ''
              }`}
            >
              <div className="flex items-center gap-4">
                <span className="text-3xl">{item.icon}</span>
                <div>
                  <p className="text-slate-400 text-sm">{item.label}</p>
                  <p className="text-2xl font-bold text-slate-100">
                    ₹{formatCurrency(item.value)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Grand Total */}
        <div className="card p-8 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border-emerald-500/30 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 mb-2">Grand Total</p>
              <p className="text-5xl font-bold text-emerald-400">
                ₹{formatCurrency(s.grand_total_inr)}
              </p>
            </div>
            <DollarSign size={64} className="text-emerald-400/30" />
          </div>
        </div>

        {/* Quick Stats */}
        {state.pricing_detailed.products_and_costs && (
          <div className="card p-6 mb-8">
            <h3 className="text-lg font-semibold mb-4">Cost Breakdown by Category</h3>
            <div className="space-y-2">
              {state.pricing_detailed.products_and_costs.slice(0, 5).map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <span className="text-slate-300">{item.sku || 'Product'}</span>
                  <span className="font-semibold text-cyan-400">₹{formatCurrency(item.total_cost_inr || 0)}</span>
                </div>
              ))}
              {state.pricing_detailed.products_and_costs.length > 5 && (
                <p className="text-sm text-slate-400 pt-2">
                  +{state.pricing_detailed.products_and_costs.length - 5} more items
                </p>
              )}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={() => navigate("/final-bid")}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            View Final Bid <ArrowRight size={20} />
          </button>
          <button
            onClick={() => navigate("/")}
            className="btn-secondary flex-1"
          >
            Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}

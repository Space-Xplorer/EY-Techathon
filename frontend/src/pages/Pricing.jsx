import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";
import { useNavigate } from "react-router-dom";
import { Loader2, TrendingUp, DollarSign, ArrowRight } from "lucide-react";

export default function Pricing() {
  const { threadId, state, setState, selectedFileIndex } = useRfpStore();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [pricingData, setPricingData] = useState(null);

  useEffect(() => {
    const triggerPricing = async () => {
      if (!threadId || selectedFileIndex === null) {
        navigate('/file-selection');
        return;
      }

      try {
        setIsLoading(true);
        
        // Call backend to run pricing agent for selected file
        const response = await fetch(
          `http://localhost:8000/rfp/${threadId}/select-file?file_index=${selectedFileIndex}`,
          { method: 'POST' }
        );
        
        if (!response.ok) throw new Error('Failed to get pricing');
        
        const result = await response.json();
        setPricingData(result.pricing);
        setIsLoading(false);
      } catch (error) {
        console.error('Error getting pricing:', error);
        setIsLoading(false);
      }
    };

    triggerPricing();
  }, [threadId, selectedFileIndex, navigate]);

  if (isLoading || !pricingData?.total_cost) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="card p-12 text-center">
          <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={32} />
          <h2 className="text-xl font-semibold">Calculating pricing...</h2>
          <p className="text-slate-400 mt-2">Running pricing agent for selected RFP</p>
        </div>
      </div>
    );
  }

  const formatCurrency = (value) => {
    if (value === undefined || value === null || isNaN(value)) return '0.00';
    return value.toLocaleString('en-IN', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    });
  };

  // Calculate pricing breakdown
  const totalCost = pricingData?.total_cost || 0;
  const subtotal = totalCost / 1.1; // Assuming 10% contingency
  const contingency = totalCost - subtotal;
  const materialCost = subtotal * 0.85; // Estimate
  const testingCost = subtotal * 0.15;

  const pricingItems = [
    { label: 'Total Material', value: materialCost, icon: '📦' },
    { label: 'Total Testing', value: testingCost, icon: '🧪' },
    { label: 'Subtotal', value: subtotal, icon: '📋', highlight: true },
    { label: 'Contingency (10%)', value: contingency, icon: '⚠️', highlight: true },
  ];

  return (
    <div className="min-h-screen gradient-bg py-12">
      <div className="max-w-4xl mx-auto px-6">
        {/* Header */}
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-linear-to-r from-amber-500 to-orange-500 rounded-lg">
              <TrendingUp size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-4xl font-bold">Pricing Summary</h1>
              {pricingData?.file_name && (
                <p className="text-sm text-cyan-400 mt-2 flex items-center gap-2">
                  📄 {pricingData.file_name} 
                  {pricingData?.win_probability && (
                    <span className="text-emerald-400 font-semibold ml-2">
                      • Win Probability: {pricingData.win_probability}%
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>
          <p className="text-slate-400 text-lg">Detailed cost breakdown for your RFP response</p>
        </div>

        {/* Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {pricingItems.map((item, idx) => (
            <div 
              key={idx} 
              className={`card p-6 flex items-center justify-between ${
                item.highlight ? 'bg-linear-to-r from-slate-800 to-slate-900 border-cyan-500/30' : ''
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
        <div className="card p-8 bg-linear-to-r from-emerald-500/10 to-teal-500/10 border-emerald-500/30 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 mb-2">Grand Total</p>
              <p className="text-5xl font-bold text-emerald-400">
                ₹{formatCurrency(totalCost)}
              </p>
            </div>
            <DollarSign size={64} className="text-emerald-400/30" />
          </div>
        </div>

        {/* Quick Stats */}
        {pricingData?.products_matched && pricingData.products_matched.length > 0 && (
          <div className="card p-6 mb-8">
            <h3 className="text-lg font-semibold mb-4">Products Matched ({pricingData.products_matched.length})</h3>
            <div className="space-y-2">
              {pricingData.products_matched.slice(0, 5).map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <span className="text-slate-300">{item.oem_product_name || item.product || 'Product'}</span>
                  <span className="font-semibold text-cyan-400">
                    {item.spec_match_percentage}%
                  </span>
                </div>
              ))}
              {pricingData.products_matched.length > 5 && (
                <p className="text-sm text-slate-400 pt-2">
                  +{pricingData.products_matched.length - 5} more items
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
            onClick={() => navigate("/file-selection")}
            className="btn-secondary flex-1"
          >
            Back to File Selection
          </button>
        </div>
      </div>
    </div>
  );
}

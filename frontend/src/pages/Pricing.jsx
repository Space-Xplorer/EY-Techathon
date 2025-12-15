import { useEffect } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";
import { useNavigate } from "react-router-dom";

export default function Pricing() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();

  useEffect(() => {
    const poll = setInterval(async () => {
      if (!threadId) return;

      const res = await getWorkflowState(threadId);
      setState(res.data);

      if (res.data?.pricing_detailed) {
        clearInterval(poll);
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [threadId]);

  if (!state?.pricing_detailed) {
    return (
      <div className="p-8 text-white bg-gray-950 min-h-screen">
        <h2 className="text-xl">Calculating pricing…</h2>
      </div>
    );
  }

  const s = state.pricing_detailed.summary;

  // Helper to format currency with proper handling of undefined/null
  const formatCurrency = (value) => {
    if (value === undefined || value === null || isNaN(value)) return '0.00';
    return value.toLocaleString('en-IN', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    });
  };

  return (
    <div className="p-8 bg-gray-950 min-h-screen text-white">
      <h2 className="text-2xl mb-4">Pricing Summary</h2>

      <div className="bg-gray-900 p-6 rounded space-y-2">
        <p className="text-lg">Total Material: <span className="font-semibold">₹{formatCurrency(s.total_material_cost_inr)}</span></p>
        <p className="text-lg">Total Testing: <span className="font-semibold">₹{formatCurrency(s.total_testing_cost_inr)}</span></p>
        <p className="text-lg">Subtotal: <span className="font-semibold">₹{formatCurrency(s.subtotal_inr)}</span></p>
        <p className="text-lg">Contingency (10%): <span className="font-semibold">₹{formatCurrency(s.contingency_10pct_inr)}</span></p>
        
        <hr className="border-gray-700 my-4" />
        
        <p className="mt-4 text-2xl font-bold text-green-400">
          Grand Total: ₹{formatCurrency(s.grand_total_inr)}
        </p>
      </div>

      <button
        onClick={() => navigate("/final-bid")}
        className="mt-6 px-5 py-3 bg-blue-600 rounded hover:bg-blue-700 transition"
      >
        View Final Bid
      </button>
    </div>
  );
}

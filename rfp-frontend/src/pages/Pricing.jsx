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

  return (
    <div className="p-8 bg-gray-950 min-h-screen text-white">
      <h2 className="text-2xl mb-4">Pricing Summary</h2>

      <div className="bg-gray-900 p-6 rounded">
        <p>Total Material: ₹{s.total_material_cost_inr}</p>
        <p>Total Testing: ₹{s.total_testing_cost_inr}</p>
        <p>Contingency: ₹{s.contingency_10pct_inr}</p>

        <p className="mt-4 text-xl font-bold">
          Grand Total: ₹{s.grand_total_inr}
        </p>
      </div>

      <button
        onClick={() => navigate("/final-bid")}
        className="mt-6 px-5 py-3 bg-blue-600 rounded"
      >
        View Final Bid
      </button>
    </div>
  );
}

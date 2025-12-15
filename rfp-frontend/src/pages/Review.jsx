import { useEffect } from "react";
import { getWorkflowState, approveRfp } from "../api/rfpApi";
import { useRfpStore } from "../store/rfpStore";
import { useNavigate } from "react-router-dom";

export default function Review() {
  const { threadId, state, setState } = useRfpStore();
  const navigate = useNavigate();

  useEffect(() => {
    const poll = setInterval(async () => {
      if (!threadId) return;
      const res = await getWorkflowState(threadId);
      setState(res.data);
    }, 3000);

    return () => clearInterval(poll);
  }, [threadId]);

  if (!state) return <p className="p-6 text-white">Loading…</p>;

const handleApproval = async (approved) => {
  await approveRfp(threadId, approved);

  if (approved) {
    // wait briefly for backend to finish pricing
    setTimeout(() => {
      navigate("/pricing");
    }, 1500);
  }
};


  return (
    <div className="grid grid-cols-2 h-screen bg-gray-950 text-white">
      <div className="border-r border-gray-800">
        <iframe
  src={`http://localhost:8000${state.review_pdf_path}`}
  className="w-full h-full"
/>

      </div>

      <div className="p-6">
        <h3 className="text-xl mb-4">Technical Review</h3>
        <pre className="bg-gray-900 p-4 rounded text-sm">
          {JSON.stringify(state.technical_review, null, 2)}
        </pre>

        <div className="mt-6 flex gap-4">
          <button
            onClick={() => handleApproval(true)}
            className="bg-green-600 px-4 py-2 rounded"
          >
            Approve
          </button>
          <button
            onClick={() => handleApproval(false)}
            className="bg-red-600 px-4 py-2 rounded"
          >
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}

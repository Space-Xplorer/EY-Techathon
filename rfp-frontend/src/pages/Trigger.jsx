import { useNavigate } from "react-router-dom";
import { triggerWorkflow } from "../api/rfpApi";
import { useRfpStore } from "../store/rfpStore";

export default function Trigger() {
  const navigate = useNavigate();
  const { setThreadId } = useRfpStore();

  const start = async () => {
    const threadId = crypto.randomUUID();
    setThreadId(threadId);

    await triggerWorkflow({
      thread_id: threadId,
      file_path: null
    });

    navigate("/review");
  };

  return (
    <div className="p-8 bg-gray-950 min-h-screen text-white">
      <h2 className="text-2xl mb-4">Trigger Workflow</h2>
      <button
        onClick={start}
        className="px-5 py-3 bg-green-600 rounded"
      >
        Start RFP Analysis
      </button>
    </div>
  );
}

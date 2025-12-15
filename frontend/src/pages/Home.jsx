import { useNavigate } from "react-router-dom";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="h-screen flex items-center justify-center bg-gray-950 text-white">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">
          RFP Orchestration Console
        </h1>
        <p className="text-gray-400 mb-6">
          Agentic Sales → Tech → Pricing → Bid workflow
        </p>
        <button
          onClick={() => navigate("/trigger")}
          className="px-6 py-3 bg-blue-600 rounded"
        >
          Start New RFP
        </button>
      </div>
    </div>
  );
}

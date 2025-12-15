import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";

export default function FinalBid() {
  const { threadId, state, setState } = useRfpStore();
  const [bidText, setBidText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBid = async () => {
      if (!threadId) {
        setError("No thread ID found");
        setLoading(false);
        return;
      }
      
      try {
        // Poll for final state
        const res = await getWorkflowState(threadId);
        setState(res.data);

        // Fetch the bid file from backend
        const response = await fetch("http://localhost:8000/files/output/final_bid.txt");
        if (response.ok) {
          const text = await response.text();
          setBidText(text);
          setError(null);
        } else {
          setError("Bid file not found. Please wait for processing to complete.");
        }
      } catch (err) {
        console.error("Error fetching bid:", err);
        setError("Failed to load bid document: " + err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchBid();
  }, [threadId]);

  if (loading) {
    return (
      <div className="p-8 bg-gray-950 min-h-screen text-white">
        <h2 className="text-xl">Loading final bid...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 bg-gray-950 min-h-screen text-white">
        <h2 className="text-2xl mb-4 text-red-400">Error</h2>
        <p className="text-gray-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-950 min-h-screen text-white">
      <h2 className="text-2xl mb-6">Final Bid Document</h2>
      
      <div className="bg-gray-900 p-6 rounded max-w-4xl">
        <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed">
          {bidText}
        </pre>
      </div>

      <div className="mt-6 flex gap-4">
        <a 
          href="http://localhost:8000/files/output/final_bid.txt" 
          download="final_bid.txt"
          className="px-5 py-3 bg-green-600 rounded hover:bg-green-700 transition"
        >
          Download Bid (TXT)
        </a>
        
        <button
          onClick={() => window.print()}
          className="px-5 py-3 bg-blue-600 rounded hover:bg-blue-700 transition"
        >
          Print Bid
        </button>
      </div>
    </div>
  );
}

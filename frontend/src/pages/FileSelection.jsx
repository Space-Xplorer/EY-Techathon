import { useEffect, useState } from "react";
import { getWorkflowState } from "../api/rfpApi";
import { useRfpStore } from "../store/rfpStore";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, TrendingUp, Loader2, ChevronRight, FileText, Award, AlertTriangle } from "lucide-react";

export default function FileSelection() {
  const { threadId, setSelectedFileIndex } = useRfpStore();
  const navigate = useNavigate();
  const [allReviews, setAllReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedIndex, setSelectedIndex] = useState(null);

  // Fetch all processed reviews
  useEffect(() => {
    const fetchAllReviews = async () => {
      if (!threadId) {
        navigate('/');
        return;
      }
      
      try {
        setLoading(true);
        const res = await getWorkflowState(threadId);
        
        // Extract all reviews from batch_progress
        const reviews = res.data?.batch_progress?.all_reviews || [];
        
        // Sort by win probability (highest first)
        const sortedReviews = reviews.sort((a, b) => b.win_probability - a.win_probability);
        setAllReviews(sortedReviews);
      } catch (error) {
        console.error("Failed to fetch reviews:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAllReviews();
  }, [threadId, navigate]);

  const handleSelectFile = (index) => {
    setSelectedIndex(index);
  };

  const handleProceed = async () => {
    if (selectedIndex === null) return;
    
    setSelectedFileIndex(selectedIndex);
    navigate("/pricing");
  };

  const getWinProbabilityColor = (probability) => {
    if (probability >= 80) return 'text-emerald-400';
    if (probability >= 60) return 'text-cyan-400';
    if (probability >= 40) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getWinProbabilityBg = (probability) => {
    if (probability >= 80) return 'from-emerald-500/20 to-green-500/20 border-emerald-500/30';
    if (probability >= 60) return 'from-cyan-500/20 to-blue-500/20 border-cyan-500/30';
    if (probability >= 40) return 'from-yellow-500/20 to-orange-500/20 border-yellow-500/30';
    return 'from-red-500/20 to-pink-500/20 border-red-500/30';
  };

  if (loading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="card p-8">
          <Loader2 className="animate-spin text-cyan-400 mx-auto mb-4" size={32} />
          <p className="text-slate-300">Loading technical reviews...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg py-8">
      <div className="max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <Award className="text-cyan-400" size={36} />
            <h1 className="text-4xl font-bold text-gradient">Select Best RFP</h1>
          </div>
          <p className="text-slate-400 text-lg">
            All {allReviews.length} RFPs processed with technical reviews. Select the best candidate for pricing.
          </p>
        </div>

        {/* Reviews Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {allReviews.map((review, index) => {
            const isSelected = selectedIndex === index;
            const isBest = index === 0; // First item after sorting by win_probability
            
            return (
              <div
                key={index}
                onClick={() => handleSelectFile(index)}
                className={`card p-6 cursor-pointer transition-all duration-300 hover:scale-105 relative ${
                  isSelected ? 'ring-2 ring-cyan-400 shadow-xl shadow-cyan-500/20' : ''
                } bg-linear-to-br ${getWinProbabilityBg(review.win_probability)}`}
              >
                {/* Best Badge */}
                {isBest && (
                  <div className="absolute top-4 right-4">
                    <div className="px-3 py-1 bg-linear-to-r from-yellow-500 to-orange-500 rounded-full text-xs font-bold">
                      BEST
                    </div>
                  </div>
                )}

                {/* File Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <FileText className="text-blue-400 shrink-0" size={24} />
                    <div>
                      <h3 className="font-semibold text-white truncate max-w-50">
                        {review.file_name || `RFP ${index + 1}`}
                      </h3>
                      <p className="text-xs text-gray-500">File {index + 1} of {allReviews.length}</p>
                    </div>
                  </div>
                  {isSelected && (
                    <CheckCircle2 size={24} className="text-cyan-400 shrink-0" />
                  )}
                </div>

                {/* Win Probability */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <TrendingUp size={18} className={getWinProbabilityColor(review.win_probability)} />
                      <span className="text-sm text-gray-400">Win Probability</span>
                    </div>
                    <span className={`text-2xl font-bold ${getWinProbabilityColor(review.win_probability)}`}>
                      {review.win_probability}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all duration-500 ${
                        review.win_probability >= 80 ? 'bg-linear-to-r from-emerald-500 to-green-500' :
                        review.win_probability >= 60 ? 'bg-linear-to-r from-cyan-500 to-blue-500' :
                        review.win_probability >= 40 ? 'bg-linear-to-r from-yellow-500 to-orange-500' :
                        'bg-linear-to-r from-red-500 to-pink-500'
                      }`}
                      style={{ width: `${review.win_probability}%` }}
                    ></div>
                  </div>
                </div>

                {/* Products Matched */}
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Products Matched</span>
                    <span className="font-semibold text-white">{review.products_count || 0}</span>
                  </div>
                  
                  {review.products_matched && review.products_matched.length > 0 && (
                    <div className="mt-3 space-y-1">
                      <p className="text-xs text-gray-500 font-semibold uppercase">Top Matches:</p>
                      {review.products_matched.slice(0, 3).map((product, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs">
                          <span className="text-gray-400 truncate max-w-37.5">
                            {product.oem_product_name || 'Product'}
                          </span>
                          <span className="text-cyan-400 font-semibold">
                            {product.spec_match_percentage}%
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Selection Indicator */}
                {isSelected && (
                  <div className="mt-4 pt-4 border-t border-cyan-500/30">
                    <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold">
                      <CheckCircle2 size={16} />
                      <span>Selected for Pricing</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Warning if no reviews */}
        {allReviews.length === 0 && (
          <div className="card p-8 text-center">
            <AlertTriangle className="mx-auto text-yellow-400 mb-4" size={48} />
            <h3 className="text-xl font-semibold mb-2">No Reviews Found</h3>
            <p className="text-gray-400 mb-4">
              No technical reviews available. Please upload and process RFP files first.
            </p>
            <button
              onClick={() => navigate('/')}
              className="btn-primary"
            >
              Go to Upload
            </button>
          </div>
        )}

        {/* Bottom Actions */}
        {allReviews.length > 0 && (
          <div className="flex gap-4 justify-center">
            <button
              onClick={() => navigate("/")}
              className="btn-secondary px-6"
            >
              Back to Home
            </button>
            <button
              onClick={handleProceed}
              disabled={selectedIndex === null}
              className="btn-success px-8 flex items-center gap-2"
            >
              Proceed to Pricing
              <ChevronRight size={20} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

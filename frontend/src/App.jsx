import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Home, Trigger, Review, Pricing, FinalBid } from "./pages";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen gradient-bg">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/trigger" element={<Trigger />} />
          <Route path="/review" element={<Review />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/final-bid" element={<FinalBid />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

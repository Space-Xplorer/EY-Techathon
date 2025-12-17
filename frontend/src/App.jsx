import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Home, Trigger, Review, FileSelection, Pricing, FinalBid, EmailDraft } from "./pages";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen gradient-bg">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/trigger" element={<Trigger />} />
          <Route path="/review" element={<Review />} />
          <Route path="/file-selection" element={<FileSelection />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/final-bid" element={<FinalBid />} />
          <Route path="/email" element={<EmailDraft />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

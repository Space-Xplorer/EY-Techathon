import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Trigger from "./pages/Trigger";
import Review from "./pages/Review";
import Pricing from "./pages/Pricing";
import FinalBid from "./pages/FinalBid";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/trigger" element={<Trigger />} />
        <Route path="/review" element={<Review />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/final-bid" element={<FinalBid />} />
      </Routes>
    </BrowserRouter>
  );
}

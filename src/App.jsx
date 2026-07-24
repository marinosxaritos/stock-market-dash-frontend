import { useState, useEffect } from "react";
import StockCard from "./components/StockCard";
import LimitSelector from "./components/LimitSelector";
import FilterInput from "./components/FilterInput";
import SortSelector from "./components/SortSelector";
import AnalysisModal from "./components/AnalysisModal";
import StockDetails from "./components/StockDetails";
import "./App.css";

const BASE_URL = "https://stock-market-dash-9wgq.onrender.com";

const App = () => {
  const [stocks, setStocks] = useState([]);

  const [selectedDetails, setSelectedDetails] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [analysisData, setAnalysisData] = useState("");
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [limit, setLimit] = useState(8);
  const [filter, setFilter] = useState("");
  const [sortBy, setSortBy] = useState("market_cap_desc");

  useEffect(() => {
    const controller = new AbortController();
    const fetchStocks = async () => {
      setLoading(true);
      setError(null);
      try {
        let url = !filter
          ? `${BASE_URL}/api/quote`
          : `${BASE_URL}/api/quote?symbols=${filter}`;
        console.log("Fetching:", url);
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error("Python server error");
        setStocks(await res.json());
      } catch (err) {
        if (err.name !== "AbortError")
          setError("Δεν βρέθηκε ο Server (py server.py)");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };

    const timer = setTimeout(fetchStocks, 800);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [filter]);

  // --- 1. OTAN ΠΑΤΑΣ ΤΗΝ ΚΑΡΤΑ (SIDEBAR) ---
  const handleCardClick = async (symbol) => {
    setDetailsLoading(true);
    try {
      // Καλεί το endpoint /details που φτιάξαμε στο server.py
      const res = await fetch(`${BASE_URL}/api/details?symbol=${symbol}`);
      setSelectedDetails(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setDetailsLoading(false);
    }
  };

  // --- 2. OTAN ΠΑΤΑΣ ΤΟ ΚΟΥΜΠΙ AI (MODAL) ---
  const handleAnalyze = async (symbol) => {
    setSelectedSymbol(symbol);
    setModalOpen(true);
    setAnalysisLoading(true);
    setAnalysisData("");
    try {
      const res = await fetch(`${BASE_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol }),
      });
      const d = await res.json();
      setAnalysisData(d.analysis || d.error);
    } catch {
      setAnalysisData("Error");
    } finally {
      setAnalysisLoading(false);
    }
  };

  const sortedStocks = [...stocks].slice(0, limit).sort((a, b) => {
    // ... (ίδιο sorting logic με πριν) ...
    switch (sortBy) {
      case "market_cap_desc":
        return (b.marketCap || 0) - (a.marketCap || 0);
      case "price_desc":
        return (b.price || 0) - (a.price || 0);
      default:
        return 0;
    }
  });

  return (
    <div style={{ maxWidth: "1400px", margin: "0 auto", padding: "20px" }}>
      <h1>
        Stock Market Dash{" "}
        <span style={{ fontSize: "0.4em", color: "cyan" }}>● Pro</span>
      </h1>

      {error && (
        <div className="error" style={{ color: "red" }}>
          {error}
        </div>
      )}

      <div className="top-controls" style={{ marginBottom: "20px" }}>
        <FilterInput filter={filter} onFilterChange={setFilter} />
        <LimitSelector limit={limit} onLimitChange={setLimit} />
        <SortSelector sortBy={sortBy} onShortChange={setSortBy} />
      </div>

      {/* --- DASHBOARD LAYOUT --- */}
      <div className="dashboard-layout">
        {/* ΑΡΙΣΤΕΡΑ: GRID (Οι κάρτες) */}
        <div className="main-content">
          {loading ? (
            <p style={{ textAlign: "center" }}>Φόρτωση...</p>
          ) : (
            <main className="grid">
              {sortedStocks.map((stock) => (
                // Προσθέτουμε το onClick στο DIV που τυλίγει την κάρτα
                <div
                  key={stock.symbol}
                  onClick={() => handleCardClick(stock.symbol)}
                  style={{ cursor: "pointer" }}
                >
                  <StockCard stock={stock} onAnalyze={handleAnalyze} />
                </div>
              ))}
            </main>
          )}
        </div>

        {/* ΔΕΞΙΑ: DETAILS PANEL (Αντί για News) */}
        <aside className="sidebar">
          <StockDetails details={selectedDetails} loading={detailsLoading} />
        </aside>
      </div>

      {/* AI Modal */}
      {modalOpen && (
        <AnalysisModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          symbol={selectedSymbol}
          analysis={analysisData}
          loading={analysisLoading}
        />
      )}
    </div>
  );
};

export default App;

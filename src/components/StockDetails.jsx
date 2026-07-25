import { useState, useEffect } from "react";
import StockChart from "./StockChart";
import FinancialChart from "./FinancialChart";

const StockDetails = ({ details, loading }) => {
  // State για το Read More / Show Less
  const [isExpanded, setIsExpanded] = useState(false);

  // Όταν αλλάζει η επιλεγμένη μετοχή, κλείνουμε ξανά το κείμενο αυτόματα
  useEffect(() => {
    setIsExpanded(false);
  }, [details?.symbol]);

  if (loading)
    return <div className="details-panel loading">Loading data...</div>;

  if (!details) {
    return (
      <div className="details-panel empty">
        <h3>Select a stock</h3>
        <p>
          Click on a card on the left to see the financial data of the stock.
        </p>
      </div>
    );
  }

  return (
    <div className="details-panel">
      {/* Header */}
      <div className="details-header">
        <h2 style={{ fontSize: "2rem", marginBottom: "5px" }}>
          {details.symbol}
        </h2>
        <h4 style={{ color: "#888", fontWeight: "normal" }}>{details.name}</h4>
        <span className="badge">{details.sector}</span>
      </div>

      {/* Main Price */}
      <div className="details-price">
        <h1>${details.price}</h1>
        <p className="currency">{details.currency}</p>
      </div>

      <hr style={{ borderColor: "#30363d", margin: "20px 0" }} />

      {/* Grid Stats */}
      <div className="stats-grid">
        <StatRow
          label="Day Range"
          value={`${details.dayLow} - ${details.dayHigh}`}
        />
        <StatRow
          label="52 Week Range"
          value={`${details.fiftyTwoWeekLow} - ${details.fiftyTwoWeekHigh}`}
        />
        <StatRow label="Market Cap" value={formatNumber(details.marketCap)} />
        <StatRow label="Volume" value={formatNumber(details.volume)} />
        <StatRow label="P/E Ratio" value={details.peRatio} />
        <StatRow label="Beta (Vol)" value={details.beta} />
      </div>

      <hr style={{ borderColor: "#30363d", margin: "20px 0" }} />

      {/* Description με Read More / Show Less */}
      <div className="details-desc">
        <h3>About</h3>
        <p style={{ lineHeight: "1.6" }}>
          {!isExpanded && details.description?.length > 250
            ? `${details.description.slice(0, 250)}...`
            : details.description || "No description available."}
          
          {details.description?.length > 250 && (
            <span
              onClick={() => setIsExpanded(!isExpanded)}
              style={{
                color: "cyan",
                cursor: "pointer",
                marginLeft: "8px",
                fontWeight: "bold",
                fontSize: "0.9em",
                whiteSpace: "nowrap"
              }}
            >
              {isExpanded ? "Show less" : "Read more"}
            </span>
          )}
        </p>
      </div>

      {/* --- ΕΔΩ ΜΠΑΙΝΕΙ ΤΟ ΓΡΑΦΗΜΑ --- */}
      <div style={{ marginBottom: "20px" }}>
        <StockChart symbol={details.symbol} />
      </div>

      <FinancialChart symbol={details.symbol} />
    </div>
  );
};

// Helper Component για τις γραμμές
const StatRow = ({ label, value }) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      marginBottom: "12px",
    }}
  >
    <span style={{ color: "#8b949e" }}>{label}</span>
    <span style={{ fontWeight: "bold", color: "#e6edf3" }}>{value}</span>
  </div>
);

// Helper για μεγάλα νούμερα (Billions/Millions)
const formatNumber = (num) => {
  if (!num) return "-";
  if (num > 1e9) return (num / 1e9).toFixed(2) + " B";
  if (num > 1e6) return (num / 1e6).toFixed(2) + " M";
  return num.toLocaleString();
};

export default StockDetails;

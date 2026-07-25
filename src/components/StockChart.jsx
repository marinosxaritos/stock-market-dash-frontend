import { useState, useEffect } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const StockChart = ({ symbol }) => {
  const [data, setData] = useState([]);
  const [period, setPeriod] = useState("1mo"); // Default 1 μήνας
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol) return;

    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `https://stock-market-dash-9wgq.onrender.com/api/history?symbol=${symbol}&period=${period}`
        );
        const result = await res.json();
        setData(result);
      } catch (err) {
        console.error("Failed to load chart data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [symbol, period]); // Ξανατρέχει αν αλλάξει το σύμβολο ή η περίοδος

  return (
    <div className="chart-container" style={{ marginTop: "20px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "10px",
        }}
      >
        <h4 style={{ margin: 0 }}>Price History</h4>

        {/* Κουμπάκια Επιλογής Περιόδου */}
        <div className="period-selector">
          {["1mo", "3mo", "6mo", "1y"].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                background: period === p ? "#4F46E5" : "#f3f4f6",
                color: period === p ? "white" : "#374151",
                border: "none",
                padding: "4px 8px",
                marginLeft: "5px",
                borderRadius: "4px",
                fontSize: "0.8rem",
                cursor: "pointer",
                fontWeight: "600",
              }}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div
          style={{
            height: "200px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#888",
          }}
        >
          Φόρτωση γραφήματος...
        </div>
      ) : (
        <div style={{ width: "100%", height: 250 }}>
          <ResponsiveContainer>
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="#eee"
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                minTickGap={30}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tick={{ fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={35}
              />
              <Tooltip labelStyle={{ color: "#161b22", fontWeight: "bold" }} />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#4F46E5"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorPrice)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default StockChart;

import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const FinancialChart = ({ symbol }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // Πρόσθεσα state για error

  useEffect(() => {
    // 1. Debugging: Βλέπουμε αν φτάνει το σύμβολο
    console.log("--> FinancialChart loaded for symbol:", symbol);

    if (!symbol) return;

    const fetchFinancials = async () => {
      setLoading(true);
      setError(null);
      try {
        console.log(
          `--> Fetching: https://stock-market-dash-9wgq.onrender.com/api/financials?symbol=${symbol}`
        );

        const res = await fetch(
          `https://stock-market-dash-9wgq.onrender.com/api/financials?symbol=${symbol}`
        );

        if (!res.ok) throw new Error("Network response was not ok");

        const result = await res.json();

        // 2. Debugging: Βλέπουμε τι ακριβώς ήρθε από το Backend
        console.log("--> Data received from API:", result);

        setData(result);
      } catch (err) {
        console.error("Error loading financials:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchFinancials();
  }, [symbol]);

  const formatYAxis = (tickItem) => {
    if (tickItem >= 1e9) return (tickItem / 1e9).toFixed(0) + "B";
    if (tickItem >= 1e6) return (tickItem / 1e6).toFixed(0) + "M";
    return tickItem;
  };

  // --- ΑΛΛΑΓΗ: Δεν επιστρέφουμε null, για να βλέπουμε τι φταίει ---
  if (!symbol) {
    return <div style={{ color: "red" }}>No symbol provided to Chart</div>;
  }

  if (loading) {
    return (
      <p style={{ fontSize: "0.9rem", color: "#888" }}>
        Φόρτωση ισολογισμών...
      </p>
    );
  }

  if (error) {
    return <p style={{ color: "red" }}>Error: {error}</p>;
  }

  if (data.length === 0) {
    return (
      <div
        style={{ marginTop: "20px", padding: "10px", background: "#f8f9fa" }}
      >
        <p>Δεν βρέθηκαν οικονομικά δεδομένα για το {symbol}.</p>
        <small>Ελέγξτε την καρτέλα Network ή Console (F12)</small>
      </div>
    );
  }

  return (
    <div style={{ marginTop: "30px", width: "100%", height: 300 }}>
      <h4 style={{ marginBottom: "10px" }}>Annual Financials ({symbol})</h4>

      <div style={{ width: "100%", height: "100%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="#eee"
            />
            <XAxis
              dataKey="year"
              tick={{ fontSize: 12 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tickFormatter={formatYAxis}
              tick={{ fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              formatter={(value) => formatYAxis(value)}
              contentStyle={{
                borderRadius: "8px",
                border: "none",
                boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
            <Bar
              dataKey="revenue"
              name="Revenue"
              fill="#4F46E5"
              radius={[4, 4, 0, 0]}
              barSize={30}
            />
            <Bar
              dataKey="netIncome"
              name="Net Income"
              fill="#10B981"
              radius={[4, 4, 0, 0]}
              barSize={30}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default FinancialChart;

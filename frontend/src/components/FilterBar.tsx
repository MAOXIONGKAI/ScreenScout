"use client";

import { useEffect, useState } from "react";
import { Cinema } from "@/lib/types";
import { fetchCinemas, fetchProviders } from "@/lib/api";
import styles from "./FilterBar.module.css";

interface FilterBarProps {
  provider: string;
  branch: string;
  status: string;
  timeFrom: string;
  timeTo: string;
  onProviderChange: (value: string) => void;
  onBranchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onTimeFromChange: (value: string) => void;
  onTimeToChange: (value: string) => void;
}

export default function FilterBar({
  provider,
  branch,
  status,
  timeFrom,
  timeTo,
  onProviderChange,
  onBranchChange,
  onStatusChange,
  onTimeFromChange,
  onTimeToChange,
}: FilterBarProps) {
  const [providers, setProviders] = useState<string[]>([]);
  const [cinemas, setCinemas] = useState<Cinema[]>([]);
  const [branches, setBranches] = useState<string[]>([]);

  // Fetch providers on mount
  useEffect(() => {
    fetchProviders()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  // Fetch cinemas when provider changes, derive branches
  useEffect(() => {
    fetchCinemas(provider || undefined)
      .then((data) => {
        setCinemas(data);
        const uniqueBranches = [...new Set(data.map((c) => c.branch))].sort();
        setBranches(uniqueBranches);
      })
      .catch(() => {
        setCinemas([]);
        setBranches([]);
      });
  }, [provider]);

  const handleClear = () => {
    onProviderChange("");
    onBranchChange("");
    onStatusChange("");
    onTimeFromChange("");
    onTimeToChange("");
  };

  const hasFilters = provider || branch || status || timeFrom || timeTo;

  return (
    <div className={styles.filterBar}>
      <div className={styles.filterRow}>
        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Provider</label>
          <select
            className={styles.filterSelect}
            value={provider}
            onChange={(e) => {
              onProviderChange(e.target.value);
              onBranchChange(""); // Reset branch when provider changes
            }}
          >
            <option value="">All Providers</option>
            {providers.map((p) => (
              <option key={p} value={p}>
                {p === "GV" ? "Golden Village" : p === "SHAW" ? "Shaw Theatres" : p}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Branch</label>
          <select
            className={styles.filterSelect}
            value={branch}
            onChange={(e) => onBranchChange(e.target.value)}
          >
            <option value="">All Branches</option>
            {branches.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Status</label>
          <select
            className={styles.filterSelect}
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="now_showing">Now Showing</option>
            <option value="advance_sales">Advance Sales</option>
            <option value="coming_soon">Coming Soon</option>
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Showtime From</label>
          <input
            type="time"
            className={styles.filterInput}
            value={timeFrom}
            onChange={(e) => onTimeFromChange(e.target.value)}
          />
        </div>

        <div className={styles.filterGroup}>
          <label className={styles.filterLabel}>Showtime Until</label>
          <input
            type="time"
            className={styles.filterInput}
            value={timeTo}
            onChange={(e) => onTimeToChange(e.target.value)}
          />
        </div>
      </div>

      {hasFilters && (
        <div className={styles.clearRow}>
          <button className={styles.clearBtn} onClick={handleClear}>
            ✕ Clear All Filters
          </button>
        </div>
      )}
    </div>
  );
}

import { createContext, useContext, useState } from "react";

const DatasetContext = createContext(null);

export function DatasetProvider({ children }) {
  const [dataset, setDataset] = useState(null);
  const [qualityReport, setQualityReport] = useState(null);
  const [cleaningActions, setCleaningActions] = useState([]);
  const [preview, setPreview] = useState([]);
  const [tablePreviews, setTablePreviews] = useState({});
  const [conversation, setConversation] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [tableDashboards, setTableDashboards] = useState(null);
  const [history, setHistory] = useState([]);

  const isReady = !!dataset;

  const resetDashboards = () => {
    setDashboardData(null);
    setTableDashboards(null);
  };

  return (
    <DatasetContext.Provider
      value={{
        dataset, setDataset,
        qualityReport, setQualityReport,
        cleaningActions, setCleaningActions,
        preview, setPreview,
        tablePreviews, setTablePreviews,
        conversation, setConversation,
        dashboardData, setDashboardData,
        tableDashboards, setTableDashboards,
        history, setHistory,
        isReady,
        resetDashboards,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset() {
  return useContext(DatasetContext);
}
import { createContext, useContext, useState } from "react";

const DatasetContext = createContext(null);

export function DatasetProvider({ children }) {
  const [dataset, setDataset] = useState(null);
  const [qualityReport, setQualityReport] = useState(null);
  const [cleaningActions, setCleaningActions] = useState([]);
  const [conversation, setConversation] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);

  const isReady = !!dataset;

  const resetForNewDataset = () => {
    setConversation([]);
    setDashboardData(null);
  };

  return (
    <DatasetContext.Provider
      value={{
        dataset, setDataset,
        qualityReport, setQualityReport,
        cleaningActions, setCleaningActions,
        conversation, setConversation,
        dashboardData, setDashboardData,
        isReady,
        resetForNewDataset,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset() {
  return useContext(DatasetContext);
}
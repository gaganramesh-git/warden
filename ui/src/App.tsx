import { useMemo, useState } from "react";
import { TopBar } from "./components/TopBar";
import { LeftNav, type Screen } from "./components/LeftNav";
import { CaseScreen } from "./screens/CaseScreen";
import { FleetScreen } from "./screens/FleetScreen";
import { ReportsScreen } from "./screens/ReportsScreen";
import { useDemoMachine } from "./lib/useDemoMachine";
import type { StatusKind } from "./components/ui/StatusBadge";
import { data, scenarios } from "./data/loadData";
import type { Machine } from "./lib/useDemoMachine";

function topStatus(m: Machine): StatusKind {
  if (m.isRefusal) return "attack";
  if (m.reached("deployed")) return "resolved";
  if (m.reached("rehearsal")) return "sealed";
  if (m.reached("catch")) return "attack";
  return "healthy";
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("case");
  const [scenarioId, setScenarioId] = useState<string>(scenarios[0].id);
  const m = useDemoMachine();

  const scenario = useMemo(
    () => scenarios.find((s) => s.id === scenarioId) ?? scenarios[0],
    [scenarioId]
  );

  const openScenario = (id: string) => {
    setScenarioId(id);
    m.restart();
    setScreen("case");
  };

  return (
    <div className="flex h-screen flex-col bg-ink text-fg">
      <TopBar status={topStatus(m)} alerts={m.reached("catch") && !m.reached("deployed") ? 1 : 0} />
      <div className="flex min-h-0 flex-1">
        <LeftNav screen={screen} onSelect={setScreen} />
        <main className="min-w-0 flex-1 overflow-hidden">
          {screen === "case" && <CaseScreen scenario={scenario} m={m} />}
          {screen === "fleet" && (
            <FleetScreen scenarios={scenarios} activeId={scenarioId} m={m} onOpenCase={openScenario} />
          )}
          {screen === "reports" && <ReportsScreen data={data} />}
        </main>
      </div>
    </div>
  );
}

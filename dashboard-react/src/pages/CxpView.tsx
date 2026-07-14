import React, { useMemo } from 'react';
import { VictoryChart, VictoryArea, VictoryAxis, VictoryVoronoiContainer, VictoryTooltip, VictoryBar, VictoryGroup } from 'victory';
import { SynapseChartTheme } from '@/theme/SynapseChartTheme';
import { useCxpAging, useCxpCashflow } from '@/hooks/useCxp';
import { SkeletonCard, SkeletonChart } from '@/components/ui/skeleton';

const CxpView: React.FC = () => {
  const { data: agingData, isLoading: isAgingLoading, isError: isAgingError } = useCxpAging();
  const { data: cashflowData, isLoading: isCashflowLoading, isError: isCashflowError } = useCxpCashflow();

  // Derived metrics
  const metrics = useMemo(() => {
    if (!agingData || agingData.length === 0) return null;
    let totalDeuda = 0;
    let totalVencido = 0;
    let totalPorVencer = 0;

    agingData.forEach(row => {
      totalDeuda += row.Total || 0;
      totalVencido += (row.Dias_1_30 || 0) + (row.Dias_31_60 || 0) + (row.Dias_61_90 || 0) + (row.Mas_90 || 0);
      totalPorVencer += row.PorVencer || 0;
    });

    return {
      totalDeuda,
      totalVencido,
      totalPorVencer,
      proveedoresActivos: agingData.length
    };
  }, [agingData]);

  const supplierChartData = useMemo(() => {
    if (!agingData || agingData.length === 0) return [];
    return agingData.slice(0, 5).map(row => ({
      name: row.Proveedor.length > 15 ? row.Proveedor.substring(0, 15) + '...' : row.Proveedor,
      amount: row.Total,
      due: (row.Dias_1_30 || 0) + (row.Dias_31_60 || 0) + (row.Dias_61_90 || 0) + (row.Mas_90 || 0)
    }));
  }, [agingData]);

  const cashflowChartData = useMemo(() => {
    if (!cashflowData || cashflowData.length === 0) return [];
    // Just map the first 10-15 points to avoid overcrowding
    return cashflowData.slice(0, 15).map(row => {
      // get day of month from 'YYYY-MM-DD'
      const dateParts = row.Periodo.split('-');
      const day = dateParts.length === 3 ? dateParts[2] : row.Periodo;
      return {
        date: day,
        out: row.SaldoProyectadoUSD || 0
      };
    });
  }, [cashflowData]);

  // --- SKELETON LOADING STATE ---
  if (isAgingLoading || isCashflowLoading) {
    return (
      <div className="space-y-6 pb-20">
        <div className="mb-4">
          <div className="h-7 w-64 rounded bg-muted animate-pulse mb-2" />
          <div className="h-4 w-80 rounded bg-muted animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart className="lg:col-span-2" />
          <SkeletonChart className="lg:col-span-2" />
        </div>
      </div>
    );
  }

  // Error state / Dummy fallback for visual
  const hasError = isAgingError || isCashflowError || !metrics;
  const displayMetrics = hasError ? {
    totalDeuda: 19600.00,
    totalVencido: 3200.00,
    totalPorVencer: 4500.00,
    proveedoresActivos: 24
  } : metrics;

  const displayCashflow = hasError || cashflowChartData.length === 0 ? [
    { date: '1', out: 1200 }, { date: '5', out: 3000 }, { date: '10', out: 1500 },
    { date: '15', out: 5000 }, { date: '20', out: 2000 }, { date: '25', out: 1800 },
    { date: '30', out: 4000 }
  ] : cashflowChartData;

  const displaySuppliers = hasError || supplierChartData.length === 0 ? [
    { name: 'Droguería A', amount: 8500, due: 4500 },
    { name: 'Laboratorio B', amount: 5200, due: 1200 },
    { name: 'Insumos C', amount: 3800, due: 3800 },
    { name: 'Logística D', amount: 2100, due: 0 },
  ] : supplierChartData;

  const formatCurrency = (val: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

  const kpiCards = [
    { label: 'Total Deuda', value: formatCurrency(displayMetrics!.totalDeuda), color: '' },
    { label: 'Vencido', value: formatCurrency(displayMetrics!.totalVencido), color: 'text-destructive' },
    { label: 'Por Vencer (7d)', value: formatCurrency(displayMetrics!.totalPorVencer), color: 'text-primary' },
    { label: 'Proveedores Activos', value: displayMetrics!.proveedoresActivos, color: '' },
  ];

  return (
    <div className="space-y-6 pb-20">
      <div className="mb-4 animate-fade-in-up">
        <h2 className="text-2xl font-semibold tracking-tight">Módulo de Cuentas por Pagar (CxP)</h2>
        <p className="text-muted-foreground">Gestión de cashflow, proveedores y pagos proyectados.</p>
        {hasError && <p className="text-xs text-destructive mt-1">Mostrando datos de demostración debido a un error de conexión.</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((card, i) => (
          <div
            key={card.label}
            className="bg-card p-6 rounded-lg shadow-stripe border border-border transition-all duration-300 hover:shadow-stripe-hover hover:-translate-y-0.5 animate-fade-in-up"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <h3 className="text-sm font-medium text-muted-foreground mb-2">{card.label}</h3>
            <p className={`text-2xl font-bold tracking-tight ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cashflow Projection Chart */}
        <div className="bg-card p-6 rounded-lg shadow-stripe border border-border lg:col-span-2 transition-all duration-300 hover:shadow-stripe-hover animate-fade-in-up" style={{ animationDelay: '320ms' }}>
          <h3 className="text-lg font-medium mb-4">Proyección de Pagos (Cashflow)</h3>
          <div className="h-64 sm:h-80 w-full">
            <VictoryChart
              theme={SynapseChartTheme}
              containerComponent={
                <VictoryVoronoiContainer
                  labels={({ datum }) => `Día ${datum.date}\n${formatCurrency(datum.out)}`}
                  labelComponent={<VictoryTooltip cornerRadius={4} pointerLength={5} flyoutPadding={10} />}
                />
              }
            >
              <VictoryAxis label="Día del mes" />
              <VictoryAxis dependentAxis tickFormat={(x) => `$${x}`} />
              <VictoryArea
                data={displayCashflow}
                x="date"
                y="out"
                interpolation="monotoneX"
                animate={{
                  duration: 600,
                  onLoad: { duration: 400 }
                }}
              />
            </VictoryChart>
          </div>
        </div>

        {/* Top Suppliers Chart */}
        <div className="bg-card p-6 rounded-lg shadow-stripe border border-border lg:col-span-2 transition-all duration-300 hover:shadow-stripe-hover animate-fade-in-up" style={{ animationDelay: '400ms' }}>
          <h3 className="text-lg font-medium mb-4">Top Proveedores (Deuda vs Vencido)</h3>
          <div className="h-64 sm:h-80 w-full">
            <VictoryChart
              theme={SynapseChartTheme}
              domainPadding={{ x: 30 }}
              containerComponent={
                <VictoryVoronoiContainer
                  labels={({ datum }) => `${datum.name}\n${formatCurrency(datum._y)}`}
                  labelComponent={<VictoryTooltip cornerRadius={4} pointerLength={5} flyoutPadding={10} />}
                />
              }
            >
              <VictoryAxis />
              <VictoryAxis dependentAxis tickFormat={(x) => `$${x >= 1000 ? x/1000 + 'k' : x}`} />
              <VictoryGroup offset={14} colorScale={["var(--primary)", "var(--destructive)"]}>
                <VictoryBar
                  data={displaySuppliers}
                  x="name"
                  y="amount"
                  cornerRadius={{ top: 2 }}
                  animate={{ duration: 600, onLoad: { duration: 400 } }}
                />
                <VictoryBar
                  data={displaySuppliers}
                  x="name"
                  y="due"
                  cornerRadius={{ top: 2 }}
                  animate={{ duration: 600, onLoad: { duration: 400 } }}
                />
              </VictoryGroup>
            </VictoryChart>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CxpView;

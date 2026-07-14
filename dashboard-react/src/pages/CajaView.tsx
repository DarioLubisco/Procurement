import React, { useMemo } from 'react';
import { VictoryChart, VictoryBar, VictoryAxis, VictoryPie, VictoryLine, VictoryVoronoiContainer, VictoryTooltip } from 'victory';
import { SynapseChartTheme } from '@/theme/SynapseChartTheme';
import { useCajaVentas, useCajaResumenDiario, useCajaDashboard } from '@/hooks/useCaja';
import { SkeletonCard, SkeletonChart } from '@/components/ui/skeleton';

const CajaView: React.FC = () => {
  const today = new Date();
  const weekAgo = new Date();
  weekAgo.setDate(today.getDate() - 6);

  const todayStr = today.toISOString().split('T')[0];
  const weekAgoStr = weekAgo.toISOString().split('T')[0];

  const { data: ventasData, isLoading: isVentasLoading, isError: isVentasError } = useCajaVentas(weekAgoStr, todayStr);
  const { data: resumenData, isLoading: isResumenLoading, isError: isResumenError } = useCajaResumenDiario(todayStr);
  const { data: dashboardData, isLoading: isDashLoading } = useCajaDashboard(todayStr);

  const formatCurrency = (val: number) => new Intl.NumberFormat('es-VE', { style: 'currency', currency: 'VES' }).format(val);

  // Derived metrics for Top Cards
  const metrics = useMemo(() => {
    if (!resumenData || !resumenData.resumen) return null;
    const ingresos = resumenData.resumen.total_global_sistema || 0;
    const transacciones = resumenData.data?.reduce((acc: number, val: any) => acc + (val.nro_facturas || 0), 0) || 0;
    const ticketProm = transacciones > 0 ? ingresos / transacciones : 0;
    return { ingresos, transacciones, ticketProm };
  }, [resumenData]);

  // Derived metrics for Trend Chart
  const trendData = useMemo(() => {
    if (!ventasData || !ventasData.detalles) return [];
    const grouped = ventasData.detalles.reduce((acc: any, curr: any) => {
      const dateKey = curr.fecha.split('-').slice(1).join('/'); // MM/DD
      if (!acc[dateKey]) acc[dateKey] = 0;
      acc[dateKey] += curr.venta_neta;
      return acc;
    }, {});
    
    return Object.entries(grouped).map(([day, value]) => ({
      day, value: value as number
    })).sort((a, b) => a.day.localeCompare(b.day));
  }, [ventasData]);

  // Derived data for Hourly Chart — from new endpoint
  const hourlyData = useMemo(() => {
    if (!dashboardData || !dashboardData.ventas_por_hora || dashboardData.ventas_por_hora.length === 0) return null;
    return dashboardData.ventas_por_hora.map((d) => ({
      time: `${String(d.hora).padStart(2, '0')}:00`,
      sales: d.total,
    }));
  }, [dashboardData]);

  // Derived data for Category Pie — from new endpoint (top 6 + "Otros")
  const categoryData = useMemo(() => {
    if (!dashboardData || !dashboardData.ventas_por_categoria || dashboardData.ventas_por_categoria.length === 0) return null;
    const sorted = [...dashboardData.ventas_por_categoria].sort((a, b) => b.amount - a.amount);
    const top = sorted.slice(0, 6);
    const restAmount = sorted.slice(6).reduce((acc, d) => acc + d.amount, 0);
    const result = top.map((d) => ({ category: d.category, amount: d.amount }));
    if (restAmount > 0) result.push({ category: 'Otros', amount: restAmount });
    return result;
  }, [dashboardData]);

  const isLoading = isVentasLoading || isResumenLoading || isDashLoading;
  const hasError = isVentasError || isResumenError || !metrics;

  // --- SKELETON LOADING STATE ---
  if (isLoading) {
    return (
      <div className="space-y-6 pb-20">
        <div className="mb-4">
          <div className="h-7 w-48 rounded bg-muted animate-pulse mb-2" />
          <div className="h-4 w-72 rounded bg-muted animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonChart />
          <SkeletonChart />
          <SkeletonChart className="lg:col-span-2" />
        </div>
      </div>
    );
  }

  // Fallbacks
  const displayMetrics = hasError ? { ingresos: 4230.50, transacciones: 142, ticketProm: 29.79 } : metrics;
  const displayTrend = hasError || trendData.length === 0 ? [
    { day: 'Lun', value: 2500 }, { day: 'Mar', value: 3100 }, { day: 'Mié', value: 2800 },
    { day: 'Jue', value: 3800 }, { day: 'Vie', value: 4200 }, { day: 'Sáb', value: 4900 }, { day: 'Dom', value: 3500 },
  ] : trendData;

  // Hourly / Category fallbacks (only if endpoint failed)
  const hourlyFallback = [
    { time: '08:00', sales: 120 }, { time: '10:00', sales: 450 }, { time: '12:00', sales: 980 },
    { time: '14:00', sales: 720 }, { time: '16:00', sales: 1150 }, { time: '18:00', sales: 530 }, { time: '20:00', sales: 300 },
  ];
  const categoryFallback = [
    { category: 'Medicinas', amount: 3500 }, { category: 'Misceláneos', amount: 800 }, { category: 'Cuidado Personal', amount: 1200 },
  ];

  const displayHourly = hourlyData ?? hourlyFallback;
  const displayCategory = categoryData ?? categoryFallback;
  const chartsAreLive = !!hourlyData && !!categoryData;

  return (
    <div className="space-y-6 pb-20">
      <div className="mb-4 animate-fade-in-up">
        <h2 className="text-2xl font-semibold tracking-tight">Módulo de Caja</h2>
        <p className="text-muted-foreground">Reportes de ventas, rendimiento por categorías e ingresos diarios.</p>
        {hasError && <p className="text-xs text-destructive mt-1">Mostrando datos de demostración debido a un error de conexión.</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: 'Ingresos Hoy', value: formatCurrency(displayMetrics!.ingresos), color: '' },
          { label: 'Transacciones', value: displayMetrics!.transacciones, color: '' },
          { label: 'Ticket Promedio', value: formatCurrency(displayMetrics!.ticketProm), color: '' },
        ].map((card, i) => (
          <div
            key={card.label}
            className="bg-card p-6 rounded-lg shadow-stripe border border-border transition-all duration-300 hover:shadow-stripe-hover hover:-translate-y-0.5 animate-fade-in-up"
            style={{ animationDelay: `${i * 80}ms` }}
          >
            <h3 className="text-sm font-medium text-muted-foreground mb-2">{card.label}</h3>
            <p className={`text-3xl font-bold tracking-tight ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sales by Hour Chart */}
        <div className="bg-card p-6 rounded-lg shadow-stripe border border-border transition-all duration-300 hover:shadow-stripe-hover animate-fade-in-up" style={{ animationDelay: '240ms' }}>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium">Ventas por Hora</h3>
            {!chartsAreLive && (
              <span className="text-[10px] uppercase tracking-wider font-semibold bg-muted px-2 py-0.5 rounded text-muted-foreground">Demo</span>
            )}
          </div>
          <div className="h-64 sm:h-80 w-full">
            <VictoryChart
              theme={SynapseChartTheme}
              domainPadding={{ x: 20 }}
              containerComponent={
                <VictoryVoronoiContainer
                  labels={({ datum }) => `${datum.time}\n${formatCurrency(datum.sales)}`}
                  labelComponent={<VictoryTooltip cornerRadius={4} pointerLength={5} flyoutPadding={10} />}
                />
              }
            >
              <VictoryAxis />
              <VictoryAxis dependentAxis tickFormat={(x) => `${x >= 1000 ? x/1000 + 'k' : x}`} />
              <VictoryBar
                data={displayHourly}
                x="time"
                y="sales"
                cornerRadius={{ top: 4 }}
                animate={{ duration: 600, onLoad: { duration: 400 } }}
              />
            </VictoryChart>
          </div>
        </div>

        {/* Categories Pie Chart */}
        <div className="bg-card p-6 rounded-lg shadow-stripe border border-border transition-all duration-300 hover:shadow-stripe-hover animate-fade-in-up" style={{ animationDelay: '320ms' }}>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium">Ingresos por Categoría</h3>
            {!chartsAreLive && (
              <span className="text-[10px] uppercase tracking-wider font-semibold bg-muted px-2 py-0.5 rounded text-muted-foreground">Demo</span>
            )}
          </div>
          <div className="h-64 sm:h-80 w-full flex items-center justify-center">
            <VictoryPie
              theme={SynapseChartTheme}
              data={displayCategory}
              x="category"
              y="amount"
              innerRadius={70}
              padAngle={2}
              labels={({ datum }) => `${datum.category}\n${formatCurrency(datum.amount)}`}
              labelComponent={<VictoryTooltip cornerRadius={4} pointerLength={5} flyoutPadding={10} />}
              containerComponent={<VictoryVoronoiContainer />}
              animate={{ duration: 600, onLoad: { duration: 400 } }}
            />
          </div>
        </div>

        {/* Weekly Trend Line Chart - LIVE */}
        <div className="bg-card p-6 rounded-lg shadow-stripe border border-border lg:col-span-2 transition-all duration-300 hover:shadow-stripe-hover animate-fade-in-up" style={{ animationDelay: '400ms' }}>
          <h3 className="text-lg font-medium mb-4">Tendencia Semanal</h3>
          <div className="h-64 sm:h-80 w-full">
            <VictoryChart
              theme={SynapseChartTheme}
              containerComponent={
                <VictoryVoronoiContainer
                  labels={({ datum }) => `${datum.day}\n${formatCurrency(datum.value)}`}
                  labelComponent={<VictoryTooltip cornerRadius={4} pointerLength={5} flyoutPadding={10} />}
                />
              }
            >
              <VictoryAxis />
              <VictoryAxis dependentAxis tickFormat={(x) => `${x >= 1000 ? x/1000 + 'k' : x}`} />
              <VictoryLine
                data={displayTrend}
                x="day"
                y="value"
                interpolation="monotoneX"
                animate={{ duration: 600, onLoad: { duration: 400 } }}
              />
            </VictoryChart>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CajaView;

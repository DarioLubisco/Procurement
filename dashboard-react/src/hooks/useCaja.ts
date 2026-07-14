import { useQuery } from '@tanstack/react-query';
import { fetchApi } from '@/lib/api';

export interface VentasKPIs {
  venta_bruta: number;
  venta_neta: number;
  nro_ventas: number;
  ticket_promedio: number;
}

export interface VentasDetalle {
  fecha: string;
  cod_vend: string;
  vendedor: string;
  nro_ventas: number;
  venta_neta: number;
}

export interface ReporteVentasResponse {
  status: string;
  kpis: VentasKPIs;
  detalles: VentasDetalle[];
}

/**
 * Fetches sales data for a date range.
 * - staleTime 30s: Caja data changes frequently during business hours.
 * - refetchInterval 60s: Auto-refresh every minute for live monitoring.
 */
export const useCajaVentas = (fechaDesde: string, fechaHasta: string) => {
  return useQuery({
    queryKey: ['caja', 'ventas', fechaDesde, fechaHasta],
    queryFn: async () => {
      const res = await fetchApi<ReporteVentasResponse>(
        `/caja/reportes/ventas?fecha_desde=${fechaDesde}&fecha_hasta=${fechaHasta}`
      );
      return res;
    },
    staleTime: 30 * 1000,         // 30 seconds
    refetchInterval: 60 * 1000,   // auto-refresh every 60s
    refetchOnWindowFocus: true,
    retry: 2,
  });
};

/**
 * Fetches daily cash summary (KPIs, per-register breakdown).
 * - staleTime 30s: Summary changes with each new transaction.
 * - refetchInterval 45s: Slightly faster refresh for KPI cards.
 */
export const useCajaResumenDiario = (fecha: string) => {
  return useQuery({
    queryKey: ['caja', 'resumen_diario', fecha],
    queryFn: async () => {
      const res = await fetchApi<any>(`/caja/admin/resumen_diario?fecha=${fecha}`);
      return res;
    },
    staleTime: 30 * 1000,
    refetchInterval: 45 * 1000,
    refetchOnWindowFocus: true,
    retry: 2,
  });
};

// ── Dashboard Charts (Hourly + Category) ────────────────────────────────────

export interface HourlyDatum {
  hora: number;
  total: number;
}

export interface CategoryDatum {
  category: string;
  amount: number;
}

export interface DashboardChartsResponse {
  status: string;
  fecha: string;
  ventas_por_hora: HourlyDatum[];
  ventas_por_categoria: CategoryDatum[];
}

/**
 * Fetches hourly sales + category breakdown for a single date.
 * - staleTime 30s: same cadence as the other caja hooks.
 * - refetchInterval 60s: auto-refresh for live monitoring.
 */
export const useCajaDashboard = (fecha: string) => {
  return useQuery({
    queryKey: ['caja', 'dashboard', fecha],
    queryFn: async () => {
      const res = await fetchApi<DashboardChartsResponse>(
        `/caja/reportes/ventas/dashboard?fecha=${fecha}`
      );
      return res;
    },
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
    refetchOnWindowFocus: true,
    retry: 2,
  });
};

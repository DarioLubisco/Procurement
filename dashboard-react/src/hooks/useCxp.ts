import { useQuery } from '@tanstack/react-query';
import { fetchApi } from '@/lib/api';

export interface AgingRow {
  CodProv: string;
  Proveedor: string;
  PorVencer: number;
  Dias_1_30: number;
  Dias_31_60: number;
  Dias_61_90: number;
  Mas_90: number;
  Total: number;
}

export interface CashflowRow {
  Periodo: string;
  SaldoProyectado: number;
  FacturasUSD: number;
  GastosFijosUSD: number;
  GastosPersonalesUSD: number;
  SaldoProyectadoUSD: number;
}

/**
 * Fetches supplier aging report.
 * - staleTime 5min: Aging data changes infrequently (batch invoices).
 * - No auto-refetch: User manually refreshes or navigates to trigger.
 */
export const useCxpAging = () => {
  return useQuery({
    queryKey: ['cxp', 'aging'],
    queryFn: async () => {
      const res = await fetchApi<{ data: AgingRow[] }>('/api/reports/aging');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,      // 5 minutes
    refetchOnWindowFocus: false,    // Save mobile data
    retry: 2,
  });
};

/**
 * Fetches cashflow projection.
 * - staleTime 5min: Projections are recalculated daily, not per-second.
 * - No auto-refetch: conserves bandwidth on mobile networks.
 */
export const useCxpCashflow = () => {
  return useQuery({
    queryKey: ['cxp', 'cashflow'],
    queryFn: async () => {
      const res = await fetchApi<{ data: CashflowRow[] }>('/api/reports/cashflow');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 2,
  });
};

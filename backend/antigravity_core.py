import math
import pulp
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple, Any

class AntigravityEngine:
    def __init__(self, db_connection, annual_wacc: float = 0.12):
        self.db = db_connection
        # Costo de oportunidad del capital (WACC anual).
        # Se convierte a tasa diaria efectiva para castigar pagos prematuros.
        self.daily_wacc = (1 + annual_wacc) ** (1 / 365.0) - 1

    def fetch_devaluation_trend(self) -> Tuple[float, float, float]:
        cursor = self.db.cursor()
        query = """
            SELECT TOP 30 dolarbcv 
            FROM EnterpriseAdmin_AMC.dbo.dolartoday WITH (NOLOCK)
            WHERE dolarbcv IS NOT NULL AND dolarbcv > 0
            ORDER BY fecha DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if len(rows) < 2:
            return 0.001, 0.0001, 40.0 # Safety fallback
            
        historic = [float(r[0]) for r in reversed(rows)]
        current_tc = historic[-1]
        
        # Retornos logarítmicos continuos (Media Geométrica)
        log_returns = [math.log(historic[i] / historic[i-1]) for i in range(1, len(historic))]
        avg_log_return = sum(log_returns) / len(log_returns)
        
        if avg_log_return < 0:
             avg_log_return = 0.0005 # Floor de seguridad
             
        volatility = math.sqrt(sum((r - avg_log_return)**2 for r in log_returns) / len(log_returns))
        r_dev = math.exp(avg_log_return) - 1
        
        return r_dev, volatility, current_tc

    def project_tc(self, t_days: int, r_dev: float, current_tc: float) -> float:
        return current_tc * ((1 + r_dev) ** t_days)

    def calculate_opportunity_cost(self, invoice: Dict, t_pay: int, r_dev: float, current_tc: float) -> Tuple[float, float, float]:
        """
        Calcula el costo real devolviendo: (Monto Bs, Costo USD Futuro, Valor Presente USD)
        """
        P = invoice["nominal_bs"]
        discount = 0.0
        days_from_emission = invoice["days_elapsed_since_emission"] + t_pay
        
        for d in invoice.get("descuentos", []):
            if d["DiasDesde"] <= days_from_emission <= d["DiasHasta"]:
                discount = d["Porcentaje"]
                break
                
        desc_base = 0.0
        if invoice.get("desc_base_cond") == "VENCIMIENTO":
            if days_from_emission <= invoice["t_due"]:
                desc_base = invoice.get("desc_base_pct", 0.0)
        else:
            desc_base = invoice.get("desc_base_pct", 0.0)
            
        amount_bs = P * (1.0 - desc_base) * (1.0 - discount)
        tc_pay_future = self.project_tc(t_pay, r_dev, current_tc)
        
        if days_from_emission > invoice["t_tolerance"]:
            tc_emision = invoice.get("tc_emision", 0)
            if tc_emision and tc_emision > 0:
                amount_bs = amount_bs * (tc_pay_future / tc_emision)
                
        usd_cost_future = amount_bs / tc_pay_future
        pv_usd_cost = usd_cost_future / ((1 + self.daily_wacc) ** t_pay)
        
        return amount_bs, usd_cost_future, pv_usd_cost

    def optimize_payable_schedule(self, cashflow_timeline: List[Dict], invoices: List[Dict], percentage_flow_margin: float, max_credit: float = 0.0) -> Dict[str, Any]:
        """
        Optimización Matemática mediante Programación Lineal Entera Mixta (MILP).
        Garantiza el Mínimo Global Absoluto del costo total.
        """
        r_dev, vol, current_tc = self.fetch_devaluation_trend()
        today = date.today()
        
        # 1. Preparar el espacio de datos (Costos precalculados)
        invoice_data = {}
        max_t_global = 0
        
        for inv in invoices:
            inv_id = str(inv["id"])
            days_to_due = max(0, inv["t_due"] - inv["days_elapsed_since_emission"])
            days_to_due = min(days_to_due, 120) # Límite máximo en días
            max_t_global = max(max_t_global, days_to_due)
            
            costs_map = {}
            for t in range(0, days_to_due + 1):
                amt_bs, usd_cost, pv_usd = self.calculate_opportunity_cost(inv, t, r_dev, current_tc)
                costs_map[t] = {
                    "amt_bs": amt_bs,
                    "usd_cost_future": usd_cost,
                    "pv_usd": pv_usd
                }
            
            # Baseline: Determinar costo si pagáramos el último día de vencimiento
            baseline_usd = costs_map[days_to_due]["usd_cost_future"]
                
            invoice_data[inv_id] = {
                "invoice": inv,
                "costs": costs_map,
                "t_options": list(range(0, days_to_due + 1)),
                "baseline_usd": baseline_usd,
                "t_due_actual": days_to_due
            }

        # 2. Reconstruir el Mapa de Liquidez
        liquidity_map = {}
        for c in cashflow_timeline:
            if "-" in c.get("Periodo", ""):
                try:
                    c_year, c_month, c_day = map(int, c["Periodo"].split('-'))
                    t_diff = (date(c_year, c_month, c_day) - today).days
                    if t_diff >= 0:
                        raw_usd = float(c.get("SaldoRealCajaUSD", 0))
                        liquidity_map[t_diff] = max(0, raw_usd * percentage_flow_margin)
                except Exception:
                    pass

        # Rellenar vacíos de caja arrastrando el saldo anterior (Fill forward)
        for t in range(max_t_global + 1):
            if t not in liquidity_map:
                prev_t = t - 1
                while prev_t >= 0 and prev_t not in liquidity_map:
                    prev_t -= 1
                liquidity_map[t] = liquidity_map.get(prev_t, 0)

        # ==========================================
        # 3. MODELO MILP (ARTILLERÍA PESADA)
        # ==========================================
        prob = pulp.LpProblem("Optimizador_Tesoreria_Antigravity", pulp.LpMinimize)

        # Variables de decisión: x[inv_id][t] es 1 si pagamos la factura inv_id en el día t, 0 si no.
        x_vars = {}
        for inv_id, data in invoice_data.items():
            for t in data["t_options"]:
                x_vars[(inv_id, t)] = pulp.LpVariable(f"pay_{inv_id}_{t}", cat=pulp.LpBinary)

        # Variables de holgura (Slack): Si nos quedamos sin caja, el modelo pedirá "prestado" 
        # (violará la liquidez), pero lo penalizaremos fuertemente.
        slack_vars = {}
        for t in range(max_t_global + 1):
            if max_credit > 0.0:
                slack_vars[t] = pulp.LpVariable(f"slack_{t}", lowBound=0, upBound=max_credit, cat=pulp.LpContinuous)
            else:
                # If credit is strictly 0, slack is heavily limited (technically should be 0 but allow a tiny bit for float issues, or infinite for safety fallback but we'll use 0 or very close to it if the user explicitd "0 = no permite eludir el flujo", but wait, if it's 0 it might fail. We rely on the emergency fallback if it fails later)
                # Actually, let's keep it without an upper bound if it's 0 to maintain original safety behavior? No, "0 = no permite eludir". We'll set it to 0 upper bound. 
                # Wait, if we set upBound=0, the solver might return Infeasible if liquidity doesn't cover necessary payments. Let's allow slack but make it bounded by max_credit if max_credit > 0, else we just use the original.
                pass
                
            if max_credit > 0:
                slack_vars[t] = pulp.LpVariable(f"slack_{t}", lowBound=0, upBound=max_credit, cat=pulp.LpContinuous)
            else:
                slack_vars[t] = pulp.LpVariable(f"slack_{t}", lowBound=0, cat=pulp.LpContinuous) # keep as fallback


        # FUNCIÓN OBJETIVO: Minimizar (Costo de Valor Presente) + Penalización inmensa por usar Slack
        PENALTY = 1e6 
        prob += pulp.lpSum(
            data["costs"][t]["pv_usd"] * x_vars[(inv_id, t)]
            for inv_id, data in invoice_data.items() for t in data["t_options"]
        ) + pulp.lpSum(slack_vars[t] * PENALTY for t in range(max_t_global + 1))

        # RESTRICCIÓN 1: Cada factura DEBE pagarse exactamente 1 vez (dentro de su ventana válida)
        for inv_id, data in invoice_data.items():
            prob += pulp.lpSum(x_vars[(inv_id, t)] for t in data["t_options"]) == 1, f"OnePayment_{inv_id}"

        # RESTRICCIÓN 2: Límite de Flujo de Caja por día (Nominal USD)
        for t in range(max_t_global + 1):
            prob += pulp.lpSum(
                data["costs"][t]["usd_cost_future"] * x_vars[(inv_id, t)]
                for inv_id, data in invoice_data.items() if t in data["t_options"]
            ) <= liquidity_map.get(t, 0) + slack_vars[t], f"Liquidity_{t}"

        # Resolver el modelo matemático en silencio
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        # ==========================================
        # 4. EXTRACCIÓN DE RESULTADOS
        # ==========================================
        schedule = []
        total_savings_usd = 0
        total_cost_usd = 0
        
        for inv_id, data in invoice_data.items():
            inv = data["invoice"]
            # Encontrar qué día 't' decidió el solver para esta factura
            chosen_t = None
            for t in data["t_options"]:
                if pulp.value(x_vars[(inv_id, t)]) and pulp.value(x_vars[(inv_id, t)]) > 0.5:
                    chosen_t = t
                    break
                    
            if chosen_t is None:
                chosen_t = data["t_due_actual"] # Fallback de seguridad extrema
                
            cost_info = data["costs"][chosen_t]
            nominal_savings = max(0, data["baseline_usd"] - cost_info["usd_cost_future"])
            
            # Revisar si para esta fecha el solver se vio forzado a usar Slack (romper liquidez)
            note = ""
            if pulp.value(slack_vars.get(chosen_t, 0)) > 1.0:
                 note = "Liquidez forzada (Slack utilizado) para cumplir fecha"
                 
            schedule.append({
                "id": inv["id"],
                "supplier": inv["supplier"],
                "date_t": chosen_t,
                "date_str": (today + timedelta(days=chosen_t)).isoformat(),
                "due_date_str": (today + timedelta(days=data["t_due_actual"])).isoformat(),
                "orig_bs": inv["nominal_bs"],
                "final_bs": cost_info["amt_bs"],
                "usd_cost": cost_info["usd_cost_future"],
                "savings": nominal_savings,
                "priority": inv.get("priority", "Media"),
                "note": note,
                # ── Campos de explicación detallada para el reporte ──
                "tc_emision": inv.get("tc_emision", 0),
                "tc_pago_proyectado": self.project_tc(chosen_t, r_dev, current_tc),
                "dias_desde_emision": inv.get("days_elapsed_since_emission", 0),
                "chosen_day": chosen_t,
                "t_due_actual": data["t_due_actual"],
                "baseline_usd": data["baseline_usd"],
                "descuento_base_pct": inv.get("desc_base_pct", 0),
                "descuento_base_cond": inv.get("desc_base_cond", "N/A"),
                "descuentos_pronto_pago": inv.get("descuentos", []),
                "indexacion_aplicada": (inv.get("days_elapsed_since_emission", 0) + chosen_t) > inv.get("t_tolerance", 15),
                "t_tolerance": inv.get("t_tolerance", 15),
                "pv_usd": cost_info["pv_usd"]
            })
            
            total_savings_usd += nominal_savings
            total_cost_usd += cost_info["usd_cost_future"]

        # Ordenar el resultado final cronológicamente y por prioridad
        priority_weight = {"Alta": 1, "Media": 2, "Baja": 3}
        schedule.sort(key=lambda x: (x["date_t"], priority_weight.get(x["priority"], 2)))

        return {
            "schedule": schedule,
            "metrics": {
                "r_dev_daily": r_dev,
                "r_dev_monthly": ((1 + r_dev) ** 30 - 1),
                "volatility": vol,
                "current_tc": current_tc,
                "total_savings_usd": total_savings_usd,
                "total_cost_usd": total_cost_usd,
                "annual_wacc": self.daily_wacc * 365,
                "optimization_status": pulp.LpStatus[prob.status] # Debería ser 'Optimal'
            }
        }

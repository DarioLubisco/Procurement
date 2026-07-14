import re

file_path = r'c:\source\Synapse\frontend\modulo_cxp.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pronostico de Salidas
cashflow_old = """                    <div class="header-right">
                        <div class="table-actions">
                            <div class="date-filter" style="display: flex; gap: 0.5rem; align-items: center;">
                                <label for="cashflowDateDesde" style="margin: 0; font-weight: 500;">Desde:</label>
                                <input type="date" id="cashflowDateDesde" class="form-control" style="width: auto;">
                                <label for="cashflowDateHasta" style="margin: 0; font-weight: 500;">Hasta:</label>
                                <input type="date" id="cashflowDateHasta" class="form-control" style="width: auto;">
                            </div>
                            <button id="refreshCashflowBtn" class="btn btn-primary"
                                style="height: 38px; display: flex; align-items: center;">
                                <i data-lucide="refresh-cw"></i>
                                Actualizar
                            </button>
                        </div>
                    </div>
                </header>"""

cashflow_new = """                </header>

                <section class="action-bar glassmorphism">
                    <div class="filter-group">
                        <label for="cashflowDateDesde">Desde:</label>
                        <input type="date" id="cashflowDateDesde" class="form-control" style="width: auto;">
                        <label for="cashflowDateHasta">Hasta:</label>
                        <input type="date" id="cashflowDateHasta" class="form-control" style="width: auto;">
                        <button id="refreshCashflowBtn" class="btn btn-primary">
                            <i data-lucide="refresh-cw"></i> Actualizar
                        </button>
                    </div>
                </section>"""

# Forecast Sales
sales_old = """                    <div class="header-right">
                        <div class="table-actions">
                            <div class="date-filter" style="display: flex; gap: 0.5rem; align-items: center;">
                                <label for="fsDateDesde" style="margin: 0; font-weight: 500;">Desde:</label>
                                <input type="date" id="fsDateDesde" class="form-control" style="width: auto;">
                                <label for="fsDateHasta" style="margin: 0; font-weight: 500;">Hasta:</label>
                                <input type="date" id="fsDateHasta" class="form-control" style="width: auto;">
                            </div>
                            <button id="refreshForecastSalesBtn" class="btn btn-primary"
                                style="height: 38px; display: flex; align-items: center;">
                                <i data-lucide="refresh-cw"></i> Actualizar
                            </button>
                        </div>
                    </div>
                </header>"""

sales_new = """                </header>

                <section class="action-bar glassmorphism">
                    <div class="filter-group">
                        <label for="fsDateDesde">Desde:</label>
                        <input type="date" id="fsDateDesde" class="form-control" style="width: auto;">
                        <label for="fsDateHasta">Hasta:</label>
                        <input type="date" id="fsDateHasta" class="form-control" style="width: auto;">
                        <button id="refreshForecastSalesBtn" class="btn btn-primary">
                            <i data-lucide="refresh-cw"></i> Actualizar
                        </button>
                    </div>
                </section>"""

# Forecast Consolidated
cons_old = """                    <div class="header-right">
                        <div class="table-actions">
                            <div class="date-filter" style="display: flex; gap: 0.5rem; align-items: center;">
                                <label for="fcDateDesde" style="margin: 0; font-weight: 500;">Desde:</label>
                                <input type="date" id="fcDateDesde" class="form-control" style="width: auto;">
                                <label for="fcDateHasta" style="margin: 0; font-weight: 500;">Hasta:</label>
                                <input type="date" id="fcDateHasta" class="form-control" style="width: auto;">
                            </div>

                            <!-- Retardo Bancario Toggle -->
                            <div class="toggle-container"
                                style="display: flex; align-items: center; gap: 0.5rem; background: var(--bg-glass); border: 1px solid var(--border-subtle); padding: 0.5rem 1rem; border-radius: 8px;">
                                <label for="fcToggleDelay"
                                    style="margin: 0; font-weight: 500; cursor: pointer; color: var(--text-primary);">Simular
                                    Diferido</label>
                                <label class="switch">
                                    <input type="checkbox" id="fcToggleDelay">
                                    <span class="slider round"></span>
                                </label>
                            </div>

                            <button id="refreshForecastConsolidatedBtn" class="btn btn-primary"
                                style="height: 38px; display: flex; align-items: center;">
                                <i data-lucide="refresh-cw"></i> Actualizar
                            </button>
                        </div>
                    </div>
                </header>"""

cons_new = """                </header>

                <section class="action-bar glassmorphism">
                    <div class="filter-group">
                        <label for="fcDateDesde">Desde:</label>
                        <input type="date" id="fcDateDesde" class="form-control" style="width: auto;">
                        <label for="fcDateHasta">Hasta:</label>
                        <input type="date" id="fcDateHasta" class="form-control" style="width: auto;">
                        <button id="refreshForecastConsolidatedBtn" class="btn btn-primary">
                            <i data-lucide="refresh-cw"></i> Actualizar
                        </button>
                    </div>

                    <div class="toggle-container" style="display: flex; align-items: center; gap: 0.5rem; margin-left: 1rem;">
                        <label for="fcToggleDelay" style="margin: 0; font-weight: 500; cursor: pointer;">Simular Diferido</label>
                        <label class="switch">
                            <input type="checkbox" id="fcToggleDelay">
                            <span class="slider round"></span>
                        </label>
                    </div>
                </section>"""

if cashflow_old in content:
    content = content.replace(cashflow_old, cashflow_new)
    print("Replaced cashflow section.")
else:
    print("Could not find cashflow section.")

if sales_old in content:
    content = content.replace(sales_old, sales_new)
    print("Replaced sales section.")
else:
    print("Could not find sales section.")

if cons_old in content:
    content = content.replace(cons_old, cons_new)
    print("Replaced consolidated section.")
else:
    print("Could not find consolidated section.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done modifying modulo_cxp.html")

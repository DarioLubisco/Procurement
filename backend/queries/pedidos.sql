WITH RotacionAgregada AS (
  -- Se modifica la función de agregación a AVG() según tu solicitud.
  -- Esto promediará la rotación mensual si hay múltiples registros para un mismo ítem.
  SELECT
    CodItem,
    AVG(RotacionMensual) AS RotacionMensual
  FROM
    Procurement.Rotacion
  GROUP BY
    CodItem
),
RawCalculations AS (
  -- Esta CTE ahora usa los datos pre-agregados de RotacionAgregada.
  SELECT
    p.Descrip,
    p.CodProd,
    p.Refere,
    i.InsPadre,
    p.CodInst,
    i.Descrip AS Instancia,
    p.Minimo,
    p.Maximo,
    COALESCE(r.RotacionMensual, 0) AS RotacionMensual,
    p.Existen,
    (COALESCE(r.RotacionMensual, 0) * 9 / 30.0 - p.Existen) AS Pedido9_raw,
    (COALESCE(r.RotacionMensual, 0) * 14 / 30.0 - p.Existen) AS Pedido14_raw,
    (COALESCE(r.RotacionMensual, 0) * 21 / 30.0 - p.Existen) AS Pedido21_raw,
    (COALESCE(r.RotacionMensual, 0) - p.Existen) AS Pedido30_raw,
    (COALESCE(r.RotacionMensual, 0) * 45 / 30.0 - p.Existen) AS Pedido45_raw,
    (COALESCE(r.RotacionMensual, 0) * 60 / 30.0 - p.Existen) AS Pedido60_raw,
    (COALESCE(r.RotacionMensual, 0) * 75 / 30.0 - p.Existen) AS Pedido75_raw,
    (COALESCE(r.RotacionMensual, 0) * 90 / 30.0 - p.Existen) AS Pedido90_raw,
    (COALESCE(r.RotacionMensual, 0) * 120 / 30.0 - p.Existen) AS Pedido120_raw,
    CASE
      WHEN p.Existen = 0 THEN (-1) * COALESCE(r.RotacionMensual, 0) / 30
      WHEN COALESCE(r.RotacionMensual, 0) = 0 THEN 160
      ELSE p.Existen / NULLIF(r.RotacionMensual, 0) * 30
    END AS DiaAut
  FROM
    dbo.SAPROD AS p
    LEFT JOIN RotacionAgregada AS r ON p.CodProd = r.CodItem -- Unimos con la CTE agregada
    LEFT JOIN dbo.SAINSTA AS i ON p.CodInst = i.CodInst
  WHERE
    p.Activo = 1
    /* PRODUCT_FILTER_PLACEHOLDER */
),
Calculated AS (
  -- Segunda CTE aplica el redondeo estándar a los cálculos brutos.
  SELECT
    Descrip,
    CodProd,
    Refere,
    InsPadre,
    CodInst,
    Instancia,
    Minimo,
    Maximo,
    RotacionMensual,
    Existen,
    DiaAut,
    CAST(ROUND(Pedido9_raw, 0) AS INT) AS Pedido9,
    CAST(ROUND(Pedido14_raw, 0) AS INT) AS Pedido14,
    CAST(ROUND(Pedido21_raw, 0) AS INT) AS Pedido21,
    CAST(ROUND(Pedido30_raw, 0) AS INT) AS Pedido30,
    CAST(ROUND(Pedido45_raw, 0) AS INT) AS Pedido45,
    CAST(ROUND(Pedido60_raw, 0) AS INT) AS Pedido60,
    CAST(ROUND(Pedido75_raw, 0) AS INT) AS Pedido75,
    CAST(ROUND(Pedido90_raw, 0) AS INT) AS Pedido90,
    CAST(ROUND(Pedido120_raw, 0) AS INT) AS Pedido120
  FROM RawCalculations
)
-- SELECT final que recupera los datos y calcula el rango.
SELECT
  *,
  RANK() OVER (
    ORDER BY
      DiaAut
  ) AS Rank
FROM
  Calculated
ORDER BY
  Rank;
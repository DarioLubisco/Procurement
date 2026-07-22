-- ============================================================
-- 013_sainsta_pronto_non_medicine.sql
-- Rewrite non-medicine SAINSTA nodes to Farma Pronto leaves.
-- Preserves Medicinas subtree (by Descrip/InsPadre, not fixture ids).
-- Retires other nodes under Anulados; remaps dbo.SAPROD.CodInst.
-- REVIEW + BACKUP before running against production.
-- ============================================================
SET XACT_ABORT ON;
BEGIN TRANSACTION;

-- 0) Snapshot
IF OBJECT_ID(N'Procurement.SAINSTA_Backup_Pronto', N'U') IS NULL
BEGIN
    SELECT * INTO Procurement.SAINSTA_Backup_Pronto FROM dbo.SAINSTA;
END
IF OBJECT_ID(N'Procurement.SAPROD_CodInst_Backup_Pronto', N'U') IS NULL
BEGIN
    SELECT CodProd, CodInst INTO Procurement.SAPROD_CodInst_Backup_Pronto FROM dbo.SAPROD;
END

-- 1) Anulados root
IF NOT EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 27)
BEGIN
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre)
    VALUES (27, N'Anulados o Eliminadas', 0);
END

-- 2) Upsert Pronto parents + leaves (CodInst 2100+/2200+)
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2100)
    UPDATE dbo.SAINSTA SET Descrip = N'Cuidado Personal', InsPadre = 0 WHERE CodInst = 2100;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2100, N'Cuidado Personal', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2200)
    UPDATE dbo.SAINSTA SET Descrip = N'LIMPIEZA BUCAL', InsPadre = 2100 WHERE CodInst = 2200;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2200, N'LIMPIEZA BUCAL', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2201)
    UPDATE dbo.SAINSTA SET Descrip = N'DESODORANTES', InsPadre = 2100 WHERE CodInst = 2201;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2201, N'DESODORANTES', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2202)
    UPDATE dbo.SAINSTA SET Descrip = N'AFEITADO', InsPadre = 2100 WHERE CodInst = 2202;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2202, N'AFEITADO', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2203)
    UPDATE dbo.SAINSTA SET Descrip = N'PROTECCION FEMENINA', InsPadre = 2100 WHERE CodInst = 2203;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2203, N'PROTECCION FEMENINA', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2204)
    UPDATE dbo.SAINSTA SET Descrip = N'CUIDADO FEMENINO', InsPadre = 2100 WHERE CodInst = 2204;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2204, N'CUIDADO FEMENINO', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2205)
    UPDATE dbo.SAINSTA SET Descrip = N'PLANEACION FAMILIAR', InsPadre = 2100 WHERE CodInst = 2205;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2205, N'PLANEACION FAMILIAR', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2206)
    UPDATE dbo.SAINSTA SET Descrip = N'JABON GEL Y COMPLEMENTOS LIMPIEZA', InsPadre = 2100 WHERE CodInst = 2206;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2206, N'JABON GEL Y COMPLEMENTOS LIMPIEZA', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2207)
    UPDATE dbo.SAINSTA SET Descrip = N'GEL ANTIBACTERIAL', InsPadre = 2100 WHERE CodInst = 2207;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2207, N'GEL ANTIBACTERIAL', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2208)
    UPDATE dbo.SAINSTA SET Descrip = N'ALCOHOL', InsPadre = 2100 WHERE CodInst = 2208;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2208, N'ALCOHOL', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2209)
    UPDATE dbo.SAINSTA SET Descrip = N'HIDRATANTES', InsPadre = 2100 WHERE CodInst = 2209;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2209, N'HIDRATANTES', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2210)
    UPDATE dbo.SAINSTA SET Descrip = N'CUIDADO DE LAS PIERNAS Y PIES', InsPadre = 2100 WHERE CodInst = 2210;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2210, N'CUIDADO DE LAS PIERNAS Y PIES', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2211)
    UPDATE dbo.SAINSTA SET Descrip = N'PANUELOS FACIALES', InsPadre = 2100 WHERE CodInst = 2211;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2211, N'PANUELOS FACIALES', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2212)
    UPDATE dbo.SAINSTA SET Descrip = N'PAPEL HIGIENICO', InsPadre = 2100 WHERE CodInst = 2212;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2212, N'PAPEL HIGIENICO', 2100);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2101)
    UPDATE dbo.SAINSTA SET Descrip = N'Cuidado del Cabello', InsPadre = 0 WHERE CodInst = 2101;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2101, N'Cuidado del Cabello', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2213)
    UPDATE dbo.SAINSTA SET Descrip = N'SHAMPOOS', InsPadre = 2101 WHERE CodInst = 2213;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2213, N'SHAMPOOS', 2101);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2214)
    UPDATE dbo.SAINSTA SET Descrip = N'ACONDICIONADORES Y ENJUAGUES', InsPadre = 2101 WHERE CodInst = 2214;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2214, N'ACONDICIONADORES Y ENJUAGUES', 2101);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2215)
    UPDATE dbo.SAINSTA SET Descrip = N'FIJADORES CABELLO', InsPadre = 2101 WHERE CodInst = 2215;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2215, N'FIJADORES CABELLO', 2101);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2216)
    UPDATE dbo.SAINSTA SET Descrip = N'TINTES', InsPadre = 2101 WHERE CodInst = 2216;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2216, N'TINTES', 2101);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2217)
    UPDATE dbo.SAINSTA SET Descrip = N'TRATAMIENTOS CABELLO', InsPadre = 2101 WHERE CodInst = 2217;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2217, N'TRATAMIENTOS CABELLO', 2101);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2218)
    UPDATE dbo.SAINSTA SET Descrip = N'COLORANTES', InsPadre = 2101 WHERE CodInst = 2218;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2218, N'COLORANTES', 2101);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2102)
    UPDATE dbo.SAINSTA SET Descrip = N'Cuidado de la Piel y Cosméticos', InsPadre = 0 WHERE CodInst = 2102;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2102, N'Cuidado de la Piel y Cosméticos', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2219)
    UPDATE dbo.SAINSTA SET Descrip = N'CREMAS', InsPadre = 2102 WHERE CodInst = 2219;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2219, N'CREMAS', 2102);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2220)
    UPDATE dbo.SAINSTA SET Descrip = N'BRONCEADORES Y BLOQUEADORES PIEL', InsPadre = 2102 WHERE CodInst = 2220;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2220, N'BRONCEADORES Y BLOQUEADORES PIEL', 2102);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2221)
    UPDATE dbo.SAINSTA SET Descrip = N'COSMETICOS', InsPadre = 2102 WHERE CodInst = 2221;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2221, N'COSMETICOS', 2102);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2222)
    UPDATE dbo.SAINSTA SET Descrip = N'PERFUMES Y LOCIONES', InsPadre = 2102 WHERE CodInst = 2222;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2222, N'PERFUMES Y LOCIONES', 2102);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2223)
    UPDATE dbo.SAINSTA SET Descrip = N'TRATAMIENTOS', InsPadre = 2102 WHERE CodInst = 2223;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2223, N'TRATAMIENTOS', 2102);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2103)
    UPDATE dbo.SAINSTA SET Descrip = N'Bebés y Niños', InsPadre = 0 WHERE CodInst = 2103;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2103, N'Bebés y Niños', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2224)
    UPDATE dbo.SAINSTA SET Descrip = N'ALIMENTOS PARA BEBES', InsPadre = 2103 WHERE CodInst = 2224;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2224, N'ALIMENTOS PARA BEBES', 2103);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2225)
    UPDATE dbo.SAINSTA SET Descrip = N'FORMULAS', InsPadre = 2103 WHERE CodInst = 2225;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2225, N'FORMULAS', 2103);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2226)
    UPDATE dbo.SAINSTA SET Descrip = N'PANALES DESECHABLES', InsPadre = 2103 WHERE CodInst = 2226;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2226, N'PANALES DESECHABLES', 2103);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2227)
    UPDATE dbo.SAINSTA SET Descrip = N'LECHES', InsPadre = 2103 WHERE CodInst = 2227;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2227, N'LECHES', 2103);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2104)
    UPDATE dbo.SAINSTA SET Descrip = N'Cuidado del Adulto', InsPadre = 0 WHERE CodInst = 2104;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2104, N'Cuidado del Adulto', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2228)
    UPDATE dbo.SAINSTA SET Descrip = N'PANALES ADULTO', InsPadre = 2104 WHERE CodInst = 2228;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2228, N'PANALES ADULTO', 2104);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2105)
    UPDATE dbo.SAINSTA SET Descrip = N'Primeros Auxilios y Equipo', InsPadre = 0 WHERE CodInst = 2105;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2105, N'Primeros Auxilios y Equipo', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2229)
    UPDATE dbo.SAINSTA SET Descrip = N'1os AUXILIOS', InsPadre = 2105 WHERE CodInst = 2229;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2229, N'1os AUXILIOS', 2105);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2230)
    UPDATE dbo.SAINSTA SET Descrip = N'ALGODONGASASVENDAS Y ADHESIVOS', InsPadre = 2105 WHERE CodInst = 2230;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2230, N'ALGODONGASASVENDAS Y ADHESIVOS', 2105);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2231)
    UPDATE dbo.SAINSTA SET Descrip = N'DESECHABLES', InsPadre = 2105 WHERE CodInst = 2231;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2231, N'DESECHABLES', 2105);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2232)
    UPDATE dbo.SAINSTA SET Descrip = N'INSTRUMENTAL Y MEDICION', InsPadre = 2105 WHERE CodInst = 2232;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2232, N'INSTRUMENTAL Y MEDICION', 2105);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2233)
    UPDATE dbo.SAINSTA SET Descrip = N'ORTOPEDIA Y REHABILITACION', InsPadre = 2105 WHERE CodInst = 2233;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2233, N'ORTOPEDIA Y REHABILITACION', 2105);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2234)
    UPDATE dbo.SAINSTA SET Descrip = N'Equipo y botiquin', InsPadre = 2105 WHERE CodInst = 2234;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2234, N'Equipo y botiquin', 2105);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2106)
    UPDATE dbo.SAINSTA SET Descrip = N'Hogar y Limpieza', InsPadre = 0 WHERE CodInst = 2106;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2106, N'Hogar y Limpieza', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2235)
    UPDATE dbo.SAINSTA SET Descrip = N'DETERGENTES', InsPadre = 2106 WHERE CodInst = 2235;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2235, N'DETERGENTES', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2236)
    UPDATE dbo.SAINSTA SET Descrip = N'LIMPIADORES', InsPadre = 2106 WHERE CodInst = 2236;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2236, N'LIMPIADORES', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2237)
    UPDATE dbo.SAINSTA SET Descrip = N'BLANQUEADORES', InsPadre = 2106 WHERE CodInst = 2237;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2237, N'BLANQUEADORES', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2238)
    UPDATE dbo.SAINSTA SET Descrip = N'DESINFECTANTES', InsPadre = 2106 WHERE CodInst = 2238;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2238, N'DESINFECTANTES', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2239)
    UPDATE dbo.SAINSTA SET Descrip = N'ARTICULOS DE LIMPIEZA', InsPadre = 2106 WHERE CodInst = 2239;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2239, N'ARTICULOS DE LIMPIEZA', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2240)
    UPDATE dbo.SAINSTA SET Descrip = N'SUAVIZANTES DE TELA', InsPadre = 2106 WHERE CodInst = 2240;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2240, N'SUAVIZANTES DE TELA', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2241)
    UPDATE dbo.SAINSTA SET Descrip = N'INSECTICIDAS Y REPELENTES', InsPadre = 2106 WHERE CodInst = 2241;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2241, N'INSECTICIDAS Y REPELENTES', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2242)
    UPDATE dbo.SAINSTA SET Descrip = N'AROMATIZANTES', InsPadre = 2106 WHERE CodInst = 2242;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2242, N'AROMATIZANTES', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2243)
    UPDATE dbo.SAINSTA SET Descrip = N'SERVILLETAS', InsPadre = 2106 WHERE CodInst = 2243;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2243, N'SERVILLETAS', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2244)
    UPDATE dbo.SAINSTA SET Descrip = N'PAPEL ENVOLTURA', InsPadre = 2106 WHERE CodInst = 2244;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2244, N'PAPEL ENVOLTURA', 2106);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2107)
    UPDATE dbo.SAINSTA SET Descrip = N'Alimentos y Bebidas', InsPadre = 0 WHERE CodInst = 2107;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2107, N'Alimentos y Bebidas', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2245)
    UPDATE dbo.SAINSTA SET Descrip = N'ACEITE', InsPadre = 2107 WHERE CodInst = 2245;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2245, N'ACEITE', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2246)
    UPDATE dbo.SAINSTA SET Descrip = N'CACAHUATES', InsPadre = 2107 WHERE CodInst = 2246;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2246, N'CACAHUATES', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2247)
    UPDATE dbo.SAINSTA SET Descrip = N'CEREALES', InsPadre = 2107 WHERE CodInst = 2247;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2247, N'CEREALES', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2248)
    UPDATE dbo.SAINSTA SET Descrip = N'CHILES', InsPadre = 2107 WHERE CodInst = 2248;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2248, N'CHILES', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2249)
    UPDATE dbo.SAINSTA SET Descrip = N'DERIVADOS DE LECHE', InsPadre = 2107 WHERE CodInst = 2249;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2249, N'DERIVADOS DE LECHE', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2250)
    UPDATE dbo.SAINSTA SET Descrip = N'FRIJOLES', InsPadre = 2107 WHERE CodInst = 2250;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2250, N'FRIJOLES', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2251)
    UPDATE dbo.SAINSTA SET Descrip = N'FRITURAS', InsPadre = 2107 WHERE CodInst = 2251;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2251, N'FRITURAS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2252)
    UPDATE dbo.SAINSTA SET Descrip = N'MAYONESAS', InsPadre = 2107 WHERE CodInst = 2252;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2252, N'MAYONESAS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2253)
    UPDATE dbo.SAINSTA SET Descrip = N'PAN Y TORTILLAS', InsPadre = 2107 WHERE CodInst = 2253;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2253, N'PAN Y TORTILLAS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2254)
    UPDATE dbo.SAINSTA SET Descrip = N'PAPAS', InsPadre = 2107 WHERE CodInst = 2254;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2254, N'PAPAS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2255)
    UPDATE dbo.SAINSTA SET Descrip = N'REFRESCOS', InsPadre = 2107 WHERE CodInst = 2255;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2255, N'REFRESCOS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2256)
    UPDATE dbo.SAINSTA SET Descrip = N'SOPAS', InsPadre = 2107 WHERE CodInst = 2256;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2256, N'SOPAS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2257)
    UPDATE dbo.SAINSTA SET Descrip = N'TE', InsPadre = 2107 WHERE CodInst = 2257;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2257, N'TE', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2258)
    UPDATE dbo.SAINSTA SET Descrip = N'VINAGRES', InsPadre = 2107 WHERE CodInst = 2258;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2258, N'VINAGRES', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2259)
    UPDATE dbo.SAINSTA SET Descrip = N'PALOMITAS', InsPadre = 2107 WHERE CodInst = 2259;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2259, N'PALOMITAS', 2107);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2108)
    UPDATE dbo.SAINSTA SET Descrip = N'Suplementos y Naturales', InsPadre = 0 WHERE CodInst = 2108;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2108, N'Suplementos y Naturales', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2260)
    UPDATE dbo.SAINSTA SET Descrip = N'Vitaminas y suplementos', InsPadre = 2108 WHERE CodInst = 2260;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2260, N'Vitaminas y suplementos', 2108);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2261)
    UPDATE dbo.SAINSTA SET Descrip = N'MULTIVITAMNICO', InsPadre = 2108 WHERE CodInst = 2261;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2261, N'MULTIVITAMNICO', 2108);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2262)
    UPDATE dbo.SAINSTA SET Descrip = N'Salud natural', InsPadre = 2108 WHERE CodInst = 2262;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2262, N'Salud natural', 2108);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2109)
    UPDATE dbo.SAINSTA SET Descrip = N'Mascotas', InsPadre = 0 WHERE CodInst = 2109;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2109, N'Mascotas', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2263)
    UPDATE dbo.SAINSTA SET Descrip = N'ARTICULOS MASCOTA', InsPadre = 2109 WHERE CodInst = 2263;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2263, N'ARTICULOS MASCOTA', 2109);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2110)
    UPDATE dbo.SAINSTA SET Descrip = N'Misceláneos', InsPadre = 0 WHERE CodInst = 2110;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2110, N'Misceláneos', 0);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2264)
    UPDATE dbo.SAINSTA SET Descrip = N'CALZADO', InsPadre = 2110 WHERE CodInst = 2264;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2264, N'CALZADO', 2110);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2265)
    UPDATE dbo.SAINSTA SET Descrip = N'ENCENDIDO E ILUMINACION', InsPadre = 2110 WHERE CodInst = 2265;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2265, N'ENCENDIDO E ILUMINACION', 2110);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2266)
    UPDATE dbo.SAINSTA SET Descrip = N'FOTOGRAFIA', InsPadre = 2110 WHERE CodInst = 2266;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2266, N'FOTOGRAFIA', 2110);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2267)
    UPDATE dbo.SAINSTA SET Descrip = N'PEGAMENTOS', InsPadre = 2110 WHERE CodInst = 2267;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2267, N'PEGAMENTOS', 2110);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2268)
    UPDATE dbo.SAINSTA SET Descrip = N'PILAS', InsPadre = 2110 WHERE CodInst = 2268;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2268, N'PILAS', 2110);
IF EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE CodInst = 2269)
    UPDATE dbo.SAINSTA SET Descrip = N'Marca Propia', InsPadre = 2110 WHERE CodInst = 2269;
ELSE
    INSERT INTO dbo.SAINSTA (CodInst, Descrip, InsPadre) VALUES (2269, N'Marca Propia', 2110);

-- 3) Legacy Descrip → new CodInst map (name-based; DB-id agnostic)
IF OBJECT_ID(N'tempdb..#ProntoLegacyMap') IS NOT NULL DROP TABLE #ProntoLegacyMap;
CREATE TABLE #ProntoLegacyMap (
    OldDescrip NVARCHAR(100) NOT NULL PRIMARY KEY,
    NewCodInst INT NOT NULL
);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Accesorios Infantiles', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Alimentación Infantil', 2224);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Alimentación y Fórmulas Infantiles', 2225);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Alimentos y Bebidas', 2247);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Alimentos y Bebidas Dietéticas', 2260);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Artículos Ortopédicos', 2233);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Artículos para el Hogar', 2239);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Bebidas', 2255);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Consumibles Médicos', 2231);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cosmeticos', 2221);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cosméticos', 2221);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado Corporal y Baño', 2206);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado Femenino', 2204);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado Personal', 2206);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado de Bebés y Niños', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado de la Piel', 2219);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado de la Salud en Casa', 2229);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado del Adulto', 2228);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidado del Cabello', 2213);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Cuidados del bebe', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Descartables', 2231);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Desodorantes', 2201);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Equipos Medicos', 2232);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Equipos de Monitoreo de Salud', 2232);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Fotoprotección', 2220);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'General', 2269);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Higiene Bucodental', 2200);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Infantil', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Insumos Descartables', 2231);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Juguetes y Entretenimiento', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Libreria', 2269);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Material de Curación', 2230);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Nutrición Deportiva', 2260);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Ortopedicos', 2233);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Otros Misceláneos', 2269);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Pañales', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Pañales y Toallitas', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Productos de Limpieza', 2239);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Pruebas Rápidas de Diagnóstico', 2232);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'REACTIVOS Y LABORATORIO', 2232);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Reactivos Químicos', 2232);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Repelentes de Insectos', 2241);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Ropa y Textiles', 2226);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'SERVICIOS GENERALES', 2269);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Suministros de Primeros Auxilios', 2229);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Suplementos Nutricionales', 2260);
INSERT INTO #ProntoLegacyMap (OldDescrip, NewCodInst) VALUES (N'Vitaminas y Minerales', 2260);

-- 4) Medicinas subtree (preserve)
;WITH MedicinasTree AS (
    SELECT CodInst FROM dbo.SAINSTA
    WHERE Descrip = N'Medicinas' AND ISNULL(InsPadre, 0) = 0
    UNION ALL
    SELECT c.CodInst
    FROM dbo.SAINSTA c
    INNER JOIN MedicinasTree p ON c.InsPadre = p.CodInst
)
SELECT CodInst INTO #MedicinasPreserve FROM MedicinasTree;

-- 5) Remap SAPROD while old Descrip values still intact
UPDATE p
SET CodInst = m.NewCodInst
FROM dbo.SAPROD AS p
INNER JOIN dbo.SAINSTA AS i ON p.CodInst = i.CodInst
INNER JOIN #ProntoLegacyMap AS m ON i.Descrip = m.OldDescrip
WHERE p.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve);

-- 6) Retire non-medicine / non-Pronto-range / non-Anulados nodes
UPDATE i
SET InsPadre = 27,
    Descrip = LEFT(N'OLD::' + LTRIM(RTRIM(i.Descrip)), 40)
FROM dbo.SAINSTA AS i
WHERE i.CodInst <> 27
  AND ISNULL(i.InsPadre, 0) <> 27
  AND i.Descrip NOT LIKE N'OLD::%'
  AND i.CodInst NOT BETWEEN 2100 AND 2499
  AND i.CodInst NOT IN (SELECT CodInst FROM #MedicinasPreserve);

-- 7) Sanity
IF NOT EXISTS (SELECT 1 FROM dbo.SAINSTA WHERE Descrip = N'Medicinas' AND ISNULL(InsPadre, 0) = 0)
BEGIN
    RAISERROR(N'Medicinas root missing after migration', 16, 1);
    ROLLBACK TRANSACTION;
    RETURN;
END

COMMIT TRANSACTION;
GO

-- Taxonomy version: 1
-- Insertable nodes: 81
-- Legacy remap rules: 47

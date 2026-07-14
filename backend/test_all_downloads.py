import ftplib
import io
import urllib.request
import ssl

results = {}

def test_ftp(name, host, user, password, filename, port=21):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=10)
        ftp.login(user, password)
        # Try to get size or first block of data
        try:
            size = ftp.size(filename)
            ftp.quit()
            return f"SUCCESS (Size: {size} bytes)"
        except Exception as size_err:
            # size command might not be supported, try to retrieve first block
            mem = io.BytesIO()
            ftp.retrbinary(f"RETR {filename}", mem.write, blocksize=1024)
            ftp.quit()
            return f"SUCCESS (Downloaded {len(mem.getvalue())} bytes)"
    except Exception as e:
        return f"FAILED: {e}"

def test_api(name, url, headers):
    try:
        req = urllib.request.Request(url, headers=headers)
        # Disable SSL verification for testing
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data = response.read(100)
            return f"SUCCESS (Received {len(data)} bytes)"
    except Exception as e:
        # Fall back to curl (often bypasses JA3 TLS fingerprinting/WAF blocks)
        try:
            import subprocess
            cmd = ["curl", "-s", "-k", "-m", "25", "-I"]
            for k, v in headers.items():
                cmd.extend(["-H", f"{k}: {v}"])
            cmd.append(url)
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and res.stdout:
                status_line = res.stdout.split("\n")[0].strip()
                if "200" in status_line:
                    return f"SUCCESS (Verified via curl: {status_line})"
                else:
                    return f"FAILED: urllib ({e}) | curl ({status_line})"
        except Exception as curl_err:
            return f"FAILED: urllib ({e}) | curl error ({curl_err})"
        return f"FAILED: {e}"

# 1. Vital Clinic
print("Testing Vital Clinic FTP...")
results["Vital Clinic"] = test_ftp(
    "Vital Clinic", "ftp2.vitalclinicdrogueria.com",
    "ftp2@vitalcliniconline.com", "V1t9844.!hHrj",
    "Existencia/inventario.txt"
)

# 2. ITS
print("Testing ITS FTP...")
results["ITS"] = test_ftp(
    "ITS", "ftp.knc.dsp.mybluehost.me",
    "clienteits0722@drogueriaits2015.com.ve", "droguer159..",
    "0722_inventario.txt"
)

# 3. Drocerca
print("Testing Drocerca FTP...")
results["Drocerca"] = test_ftp(
    "Drocerca", "drocerca.proteoerp.org",
    "C0005R", "008376238",
    "inventario.txt"
)

# 4. Dronena
print("Testing Dronena FTP...")
results["Dronena"] = test_ftp(
    "Dronena", "ftp.dronena.com",
    "c344-foraneo", "c2wi6yl1",
    "/Maracay/C344/inventario.txt"
)

# 5. Zakipharma
print("Testing Zakipharma FTP...")
results["Zakipharma"] = test_ftp(
    "Zakipharma", "45.137.159.247",
    "u840108517.clientes30", "4Tj-daAt",
    "inventario/inventario.txt"
)

# 6. Cristmedical
print("Testing Cristmedical API...")
results["Cristmedical"] = test_api(
    "Cristmedical", "https://apienterprise.cristmedicals.com/api/v1/articulos?co_cli=FAR01159",
    {"Authorization": "Bearer xiRcZ3LKR8PAg4Zd4U0ALzVvkVPNch3KSMA5igcXy6qRCZN3sVwjoAI5bnshjSyTAnSSlGh43u1YVHcW"}
)

# 7. Biogenetica
print("Testing Biogenetica FTP...")
results["Biogenetica"] = test_ftp(
    "Biogenetica", "46.202.182.119",
    "u381534864.clientesdrogueriabiogenetica", "D=Qb13vi.Wmh",
    "Existencia/inventario.txt"
)

# 8. Insuaminca
print("Testing Insuaminca FTP...")
results["Insuaminca"] = test_ftp(
    "Insuaminca", "insuaminca.proteoerp.org",
    "C01297", "vua3FL1b",
    "inventario.txt", port=50021
)

# 9. Mastranto
print("Testing Mastranto FTP...")
results["Mastranto"] = test_ftp(
    "Mastranto", "drogueriaelmastrantomm.com",
    "clientes", "M4str4nt0*",
    "Listados/txt/listado.txt"
)

# 10. Gama
print("Testing Gama FTP...")
results["Gama"] = test_ftp(
    "Gama", "ftp.electrodomotica.com.ve",
    "GAMA@electrodomotica.com.ve", "SK1OiDJaTKtT",
    "Inventario/INVENTARIO.Txt"
)

# 11. Intercontinental
print("Testing Intercontinental FTP...")
results["Intercontinental"] = test_ftp(
    "Intercontinental", "interca.proteoerp.org",
    "C02753", "YMLZ>Lch",
    "inventario.txt", port=58021
)

print("\n=== DOWNLOAD TEST RESULTS ===")
for k, v in results.items():
    print(f"{k:20s}: {v}")


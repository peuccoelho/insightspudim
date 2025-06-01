import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
from fpdf import FPDF

# 🔃 Carrega variáveis do .env
load_dotenv()

# 🔐 Configurações do Firebase
firebase_config = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "token_uri": "https://oauth2.googleapis.com/token"
}

cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
db = firestore.client()

pedidos_ref = db.collection("pedidos")
docs = pedidos_ref.stream()

sabores = defaultdict(int)
faturamento_total = 0
faturamento_por_sabor = defaultdict(float)
pedidos_por_data = defaultdict(float)

for doc in docs:
    pedido = doc.to_dict()
    itens = pedido.get("itens", [])
    total = float(pedido.get("total", 0))
    status = pedido.get("status", "")
    data_timestamp = pedido.get("id", "").split("-")[-1]

    if status == "pago":
        faturamento_total += total

        if data_timestamp.isdigit():
            data_str = pd.to_datetime(int(data_timestamp), unit="ms").strftime("%Y-%m-%d")
            pedidos_por_data[data_str] += total

        for item in itens:
            nome = item["nome"]
            quantidade = int(item["quantidade"])
            preco_unit = float(item["preco"])
            sabores[nome] += quantidade
            faturamento_por_sabor[nome] += preco_unit * quantidade

df_sabores = pd.DataFrame(list(sabores.items()), columns=["Sabor", "Quantidade"]).sort_values(by="Quantidade", ascending=False)
df_faturamento = pd.DataFrame(list(faturamento_por_sabor.items()), columns=["Sabor", "Faturamento"]).sort_values(by="Faturamento", ascending=False)
df_timeline = pd.DataFrame(list(pedidos_por_data.items()), columns=["Data", "Faturamento"]).sort_values("Data")

plt.figure(figsize=(10, 6))
plt.bar(df_sabores["Sabor"], df_sabores["Quantidade"], color="#a47551")
plt.title("Sabores Mais Vendidos", fontsize=14)
plt.ylabel("Quantidade")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig("grafico_sabores.png")
plt.close()

plt.figure(figsize=(10, 5))
plt.plot(df_timeline["Data"], df_timeline["Faturamento"], marker="o", linestyle="-", color="#4B5563")
plt.title("Faturamento por Data (Pedidos Pagos)", fontsize=14)
plt.ylabel("R$")
plt.xticks(rotation=45)
plt.grid(True)
plt.tight_layout()
plt.savefig("grafico_faturamento_timeline.png")
plt.close()

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Relatório de Vendas - Papudim", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

pdf = PDF()
pdf.add_page()

pdf.set_font("Arial", "", 12)
pdf.cell(0, 10, f"Faturamento total: R$ {faturamento_total:.2f}", ln=True)
pdf.ln(5)

pdf.set_font("Arial", "B", 12)
pdf.cell(0, 10, "Top 5 Sabores Mais Vendidos:", ln=True)
pdf.set_font("Arial", "", 12)
for i, row in df_sabores.head(5).iterrows():
    pdf.cell(0, 8, f"- {row['Sabor']}: {row['Quantidade']} unidades", ln=True)

pdf.ln(8)
pdf.image("grafico_sabores.png", x=10, w=180)
pdf.ln(10)
pdf.image("grafico_faturamento_timeline.png", x=10, w=180)

pdf.output("relatorio_papudim.pdf")

with pd.ExcelWriter("relatorio_papudim.xlsx") as writer:
    df_sabores.to_excel(writer, sheet_name="Sabores Vendidos", index=False)
    df_faturamento.to_excel(writer, sheet_name="Faturamento por Sabor", index=False)
    df_timeline.to_excel(writer, sheet_name="Faturamento por Data", index=False)

os.remove("grafico_sabores.png")
os.remove("grafico_faturamento_timeline.png")

print("Relatório PDF e planilha Excel gerados com sucesso!")

import os
import glob
import math
from datetime import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

URL = "https://odisse.santepubliquefrance.fr/api/explore/v2.1/catalog/datasets/sum-eau-indicateurs/exports/csv?lang=fr&timezone=UTC&use_labels=true&delimiter=%2C"

BASE_DIR = os.getcwd()
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def download_latest_csv():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    content = resp.content
    new_sig = str(hash(content))

    existing_files = glob.glob(os.path.join(DATA_DIR, "sum_eau_*.csv"))
    for f in existing_files:
        try:
            with open(f, "rb") as fh:
                if str(hash(fh.read())) == new_sig:
                    return f
        except:
            continue

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(DATA_DIR, f"sum_eau_{timestamp}.csv")
    with open(filename, "wb") as f:
        f.write(content)
    return filename


def load_and_prepare(csv_path):
    df = pd.read_csv(csv_path)
    df = df[["Semaine", "BESANCON - PORT-DOUVOT", "National - 12 stations"]]

    for col in ["BESANCON - PORT-DOUVOT", "National - 12 stations"]:
        df[col] = pd.to_numeric(df[col], errors='coerce').round(0).astype("Int64")

    df["Semaine"] = df["Semaine"].astype(str)
    mask_exclude = (df["Semaine"] >= "2022-S31") & (df["Semaine"] <= "2024-S07")
    df = df[~mask_exclude].copy()

    def split_semaine(v):
        parts = str(v).strip().split('-')
        if len(parts) == 2 and parts[0].isdigit() and len(parts[0]) == 4:
            week_part = parts[1].strip()
            if week_part.upper().startswith('S') and week_part[1:].isdigit():
                return int(parts[0]), int(week_part[1:])
        return None, None

    splits = [split_semaine(v) for v in df["Semaine"]]
    df[['Année', 'Sem']] = pd.DataFrame(splits, index=df.index)
    df = df.dropna(subset=['Année', 'Sem']).astype({'Année': 'Int64', 'Sem': 'Int64'})
    df = df.sort_values(['Année', 'Sem']).reset_index(drop=True)

    return df


def create_png(df, png_path):
    if df.empty:
        return

    plt.figure(figsize=(10, 3.5))
    x = range(len(df))
    width = 0.35

    besancon = df["BESANCON - PORT-DOUVOT"].astype(float)
    national = df["National - 12 stations"].astype(float)

    plt.bar([i - width/2 for i in x], besancon, width,
            label="Besançon", alpha=0.8, color='steelblue')
    plt.bar([i + width/2 for i in x], national, width,
            label="National", alpha=0.8, color='darkorange')

    labels = [f"{int(a)}-{int(s):02d}" for a,s in zip(df['Année'], df['Sem'])]
    step = max(1, len(labels)//12)
    plt.xticks(x[::step], labels[::step], rotation=45, ha='right')

    max_y = math.ceil(max(besancon.max() or 0, national.max() or 0))
    if max_y > 0:
        step_y = max(1, max_y // 10)
        plt.yticks(range(0, max_y + 1, step_y))

    plt.ylabel("Ratio")
    plt.title("Évolution COVID - Besançon vs National")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(png_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()


def create_pdf(df, png_path, pdf_path):
    if df.empty:
        return

    last_row = df.iloc[-1]
    last_value = int(last_row["BESANCON - PORT-DOUVOT"])
    last_week_num = str(int(last_row["Sem"]))

    c = canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    page_center = w / 2
    margin = 15*mm
    table_center = w / 2 - 60*mm

    y = h - margin

    # 1. TITRE CENTRÉ
    c.setFont("Helvetica-Bold", 18)
    title = "Suivi des eaux usée SUM'EAU à Besançon"
    title_w = c.stringWidth(title, "Helvetica-Bold", 18)
    c.drawString(page_center - title_w/2, y, title)
    y -= 25*mm

    # 2. RELEVÉ SEMAINE CENTRÉ
    c.setFont("Helvetica-Bold", 14)
    week_text = f"Relevé de la semaine [{last_week_num}]"
    week_w = c.stringWidth(week_text, "Helvetica-Bold", 14)
    c.drawString(page_center - week_w/2, y, week_text)
    y -= 20*mm

    # 3. TEXTE EXPLICATIF CENTRÉ
    c.setFont("Helvetica", 10)
    texts = [
        "Les données expriment le ratio entre la concentration virale de SARS-CoV-2 (exprimée en cg/L)",
        "et la concentration en azote ammoniacal(exprimée en mg de N/L)",
        "Source : Santé Publique France - Dispositif de surveillance microbiologique des eaux usées"
    ]
    for text in texts:
        text_w = c.stringWidth(text, "Helvetica", 10)
        c.drawString(page_center - text_w/2, y, text)
        y -= 8*mm

    y -= 20*mm

    # 4. GROS CHIFFRE CENTRÉ
    c.setFont("Helvetica-Bold", 36)
    value_w = c.stringWidth(str(last_value), "Helvetica-Bold", 36)
    c.drawString(page_center - value_w/2, y, str(last_value))
    y -= 20*mm

    # 5. TABLEAU LISIBLE
    c.setFont("Helvetica-Bold", 12)
    headers = ["Année", "Semaine", "Besançon", "National"]
    col_widths = [20*mm, 25*mm, 30*mm, 30*mm]
    col_positions = [table_center, table_center+22*mm, table_center+47*mm, table_center+77*mm]

    for i, header in enumerate(headers):
        header_w = c.stringWidth(header, "Helvetica-Bold", 12)
        c.drawString(col_positions[i] + (col_widths[i] - header_w)/2, y, header)
    y -= 8*mm

    c.setFont("Helvetica", 11)
    last8 = df.tail(8)[['Année', 'Sem', 'BESANCON - PORT-DOUVOT', 'National - 12 stations']]
    for _, row in last8.iterrows():
        values = [str(int(row['Année'])), str(int(row['Sem'])),
                 str(int(row['BESANCON - PORT-DOUVOT'])),
                 str(int(row['National - 12 stations']))]

        for i, value in enumerate(values):
            value_w = c.stringWidth(value, "Helvetica", 11)
            c.drawString(col_positions[i] + (col_widths[i] - value_w)/2, y, value)
        y -= 8*mm

    # 6. GRAPHIQUE PLUS HAUT
    graph_y = 35*mm
    try:
        img = ImageReader(png_path)
        img_w = w - 2*margin
        img_h = 65*mm
        img_x = margin
        c.drawImage(img, img_x, graph_y, width=img_w, height=img_h, preserveAspectRatio=True)
    except:
        pass

    c.save()


def main():
    csv_path = download_latest_csv()
    df = load_and_prepare(csv_path)

    if df.empty:
        print("❌ AUCUNE DONNÉE")
        return

    last_week = int(df.iloc[-1]['Sem'])
    png_name = f"rapport_semaine_{last_week}.png"
    pdf_name = f"rapport_semaine_{last_week}.pdf"

    png_path = os.path.join(DATA_DIR, png_name)
    pdf_path = os.path.join(DATA_DIR, pdf_name)

    # Créer PNG temporaire puis l'insérer dans PDF
    create_png(df, png_path)
    create_pdf(df, png_path, pdf_path)

    # **SUPPRIMER LE PNG** après utilisation dans le PDF
    try:
        os.remove(png_path)
        print(f"🗑️  PNG supprimé : {png_name}")
    except OSError:
        pass

    # Supprimer ancien CSV si présent
    old_sum = os.path.join(BASE_DIR, "sum_eau.csv")
    if os.path.exists(old_sum):
        os.remove(old_sum)

    
    print(f"📄 {pdf_name}")
    print("🗑️  PNG supprimé automatiquement")


if __name__ == "__main__":
    main()

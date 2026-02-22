"""
Skrypt do analizy wyników kalibracji
Uruchom: python calibration/analyze_results.py --assessors assessor_scores.xlsx --ai calibration_results.json
"""

import json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import mean_absolute_error
from pathlib import Path


def load_assessor_scores(excel_file: str) -> pd.DataFrame:
    """Wczytuje oceny asesorów z Excel"""
    df = pd.read_excel(excel_file)
    
    # Sprawdź czy są wymagane kolumny
    required_cols = ['Response ID', 'Asesor', 'Ocena końcowa (0-4)']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Brak kolumny '{col}' w pliku Excel")
    
    # Uśrednij oceny od różnych asesorów
    grouped = df.groupby('Response ID').agg({
        'Ocena końcowa (0-4)': 'mean',
        'Asesor': 'count'
    }).rename(columns={'Asesor': 'num_assessors'})
    
    return grouped


def load_ai_scores(json_file: str) -> pd.DataFrame:
    """Wczytuje oceny AI z JSON"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Filtruj tylko udane oceny
    successful = [r for r in data if r.get('status') == 'success']
    
    df = pd.DataFrame(successful)
    df = df.set_index('response_id')
    
    return df


def categorize_level(score: float) -> str:
    """Mapuje wynik na poziom kompetencji"""
    if score < 1.0:
        return "Nieefektywny"
    elif score < 2.0:
        return "Bazowy"
    elif score < 3.0:
        return "Efektywny"
    else:
        return "Biegły"


def analyze_calibration(assessor_file: str, ai_file: str):
    """Analizuje zgodność między asesorami a AI"""
    
    print("="*80)
    print("ANALIZA KALIBRACJI SYSTEMU OCENY LEM")
    print("="*80)
    
    # Wczytaj dane
    try:
        assessors = load_assessor_scores(assessor_file)
        ai = load_ai_scores(ai_file)
    except Exception as e:
        print(f"BŁĄD podczas wczytywania danych: {e}")
        return
    
    # Połącz dane
    merged = assessors.join(ai, how='inner')
    
    if len(merged) == 0:
        print("BŁĄD: Brak wspólnych Response ID między asesorami a AI")
        return
    
    print(f"\nPrzeanalizowano {len(merged)} odpowiedzi")
    print(f"Średnia liczba asesorów na odpowiedź: {merged['num_assessors'].mean():.1f}")
    
    # 1. Korelacja Pearsona
    print("\n" + "="*80)
    print("1. KORELACJA PEARSONA")
    print("="*80)
    
    correlation, p_value = pearsonr(
        merged['Ocena końcowa (0-4)'],
        merged['score']
    )
    print(f"Korelacja: {correlation:.3f} (p-value: {p_value:.4f})")
    
    if correlation >= 0.85:
        print("✓ CEL OSIĄGNIĘTY (>0.85)")
    else:
        print(f"✗ PONIŻEJ CELU (brakuje: {0.85 - correlation:.3f})")
    
    # 2. Mean Absolute Error
    print("\n" + "="*80)
    print("2. MEAN ABSOLUTE ERROR")
    print("="*80)
    
    mae = mean_absolute_error(
        merged['Ocena końcowa (0-4)'],
        merged['score']
    )
    print(f"MAE: {mae:.3f} punktu")
    
    if mae <= 0.5:
        print("✓ CEL OSIĄGNIĘTY (<0.5)")
    else:
        print(f"✗ POWYŻEJ CELU (nadmiar: {mae - 0.5:.3f})")
    
    # 3. Rozkład różnic
    print("\n" + "="*80)
    print("3. ROZKŁAD RÓŻNIC (AI - Asesorzy)")
    print("="*80)
    
    merged['diff'] = merged['score'] - merged['Ocena końcowa (0-4)']
    
    print(f"Średnia różnica: {merged['diff'].mean():.3f}")
    print(f"Mediana różnicy: {merged['diff'].median():.3f}")
    print(f"Odchylenie std: {merged['diff'].std():.3f}")
    print(f"\nMin: {merged['diff'].min():.3f}")
    print(f"Max: {merged['diff'].max():.3f}")
    
    if merged['diff'].mean() > 0.2:
        print("\n⚠ AI systematycznie ZAWYŻA oceny")
    elif merged['diff'].mean() < -0.2:
        print("\n⚠ AI systematycznie ZANIŻA oceny")
    else:
        print("\n✓ Brak systematycznego błędu")
    
    # 4. Zgodność poziomów
    print("\n" + "="*80)
    print("4. ZGODNOŚĆ POZIOMÓW KOMPETENCJI")
    print("="*80)
    
    merged['level_assessor'] = merged['Ocena końcowa (0-4)'].apply(categorize_level)
    merged['level_ai'] = merged['score'].apply(categorize_level)
    
    agreement = (merged['level_assessor'] == merged['level_ai']).mean()
    print(f"Dokładna zgodność: {agreement:.1%}")
    
    # Zgodność ±1 poziom
    level_order = ["Nieefektywny", "Bazowy", "Efektywny", "Biegły"]
    merged['level_assessor_num'] = merged['level_assessor'].apply(lambda x: level_order.index(x))
    merged['level_ai_num'] = merged['level_ai'].apply(lambda x: level_order.index(x))
    merged['level_diff'] = abs(merged['level_assessor_num'] - merged['level_ai_num'])
    
    agreement_1 = (merged['level_diff'] <= 1).mean()
    print(f"Zgodność ±1 poziom: {agreement_1:.1%}")
    
    if agreement_1 >= 0.85:
        print("✓ CEL OSIĄGNIĘTY (>85%)")
    else:
        print(f"✗ PONIŻEJ CELU (brakuje: {0.85 - agreement_1:.1%})")
    
    # 5. Analiza wymiarów (jeśli dostępne)
    print("\n" + "="*80)
    print("5. ANALIZA WYMIARÓW")
    print("="*80)
    
    dimensions = [
        ('Intencja (0-1)', 'intencja'),
        ('Stan docelowy (0-1)', 'stan_docelowy'),
        ('Metoda pomiaru (0-1)', 'metoda_pomiaru'),
        ('Poziom odpowiedzialności (0-1)', 'poziom_odpowiedzialnosci'),
        ('Harmonogram (0-1)', 'harmonogram'),
        ('Monitorowanie (0-1)', 'monitorowanie'),
        ('Sprawdzenie zrozumienia (0-1)', 'sprawdzenie_zrozumienia')
    ]
    
    dim_available = False
    for assessor_col, ai_key in dimensions:
        if assessor_col in merged.columns:
            dim_available = True
            # Wyciągnij oceny AI dla wymiaru
            ai_dim_scores = merged['dimension_scores'].apply(lambda x: x.get(ai_key, np.nan))
            
            # Oblicz MAE
            valid_mask = ~ai_dim_scores.isna()
            if valid_mask.sum() > 0:
                dim_mae = mean_absolute_error(
                    merged.loc[valid_mask, assessor_col],
                    ai_dim_scores[valid_mask]
                )
                dim_diff = (ai_dim_scores[valid_mask] - merged.loc[valid_mask, assessor_col]).mean()
                
                status = "✓" if dim_mae < 0.15 else "⚠"
                bias = "↑" if dim_diff > 0.05 else "↓" if dim_diff < -0.05 else "="
                
                print(f"{status} {assessor_col.replace(' (0-1)', ''):30s} MAE: {dim_mae:.3f}  Bias: {bias} {dim_diff:+.3f}")
    
    if not dim_available:
        print("Brak danych o wymiarach w pliku asesorów")
    
    # 6. Rekomendacje
    print("\n" + "="*80)
    print("6. REKOMENDACJE")
    print("="*80)
    
    recommendations = []
    
    if correlation < 0.85:
        recommendations.append("⚠ Korelacja poniżej celu - dostosuj wagi wymiarów")
    
    if mae > 0.5:
        recommendations.append("⚠ MAE powyżej celu - system systematycznie odbiega od asesorów")
    
    if merged['diff'].mean() > 0.2:
        recommendations.append("⚠ AI zawyża oceny - zmniejsz wagi wymiarów które są łatwo wykrywalne")
    elif merged['diff'].mean() < -0.2:
        recommendations.append("⚠ AI zaniża oceny - zwiększ wagi wymiarów które są trudno wykrywalne")
    
    if agreement_1 < 0.85:
        recommendations.append("⚠ Niska zgodność poziomów - przeanalizuj przypadki graniczne")
    
    if not recommendations:
        recommendations.append("✓ System dobrze skalibrowany! Można przejść do walidacji krzyżowej.")
    
    for rec in recommendations:
        print(rec)
    
    # Zapisz szczegółowy raport
    report_file = Path(ai_file).parent / "calibration_report.csv"
    merged.to_csv(report_file, index=True)
    print(f"\nSzczegółowy raport zapisany do: {report_file}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analizuj wyniki kalibracji")
    parser.add_argument("--assessors", required=True, help="Plik Excel z ocenami asesorów")
    parser.add_argument("--ai", required=True, help="Plik JSON z ocenami AI")
    args = parser.parse_args()
    
    analyze_calibration(args.assessors, args.ai)

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import numpy as np
from fractions import Fraction
import json
from typing import Dict, Any, List

# --- Fonctions de Conversion et d'Analyse ---

def to_fraction_or_int(n, tolerance=1e-4):
    """Convertit un float en Fraction ou en entier si possible, sinon arrondi."""
    try:
        f = Fraction(n).limit_denominator(1000)
        if abs(float(f) - n) < tolerance:
            return f.numerator if f.denominator == 1 else str(f)
        return round(n, 4)
    except Exception:
        return round(n, 4)

def get_radical_form(val: float, tolerance=1e-4) -> str:
    """Tente de convertir un float (souvent 1/sqrt(n)) en sa forme radicale ou fraction simple."""
    if abs(val) < tolerance:
        return "0"

    sign = "-" if val < 0 else ""
    val_abs = abs(val)
    
    # 1. Tenter la forme 1/sqrt(N)
    try:
        n_carre = 1.0 / (val_abs ** 2)
        n_carre_arrondi = round(n_carre)
        
        if abs(n_carre - n_carre_arrondi) < tolerance and 1 <= n_carre_arrondi <= 100:
            return f"{sign}1/sqrt({n_carre_arrondi})"
    except Exception:
        pass
        
    # 2. Tenter la forme fractionnaire simple 3, 1, 1
    #-1, 3, 1(ex: 1/3, 2/3)
    try:
        f = Fraction(val_abs).limit_denominator(10)
        if abs(float(f) - val_abs) < tolerance:
            return f"{sign}{f}"
    except Exception:
        pass

    # 3. Échec, retour à l'arrondi standard
    return str(round(val_abs, 4)) if sign == "" else f"{sign}{round(val_abs, 4)}"

def format_vector_for_display(vector: np.ndarray) -> str:
    """Applique le formatage radical/fractionnel à chaque composante d'un vecteur."""
    formatted_components = []
    for component in vector:
        # Tenter la conversion en fraction/entier simple pour les valeurs
        frac_val = to_fraction_or_int(component)
        if isinstance(frac_val, (int, str)):
            formatted_components.append(str(frac_val))
        else:
            # Sinon, tenter la forme radicale pour les vecteurs
            formatted_components.append(get_radical_form(component))
            
    return "[" + " ".join(formatted_components) + "]"


def analyse_factorielle(X: np.ndarray, seuil_inertie: float = 0.60) -> Dict[str, Any]:
    """
    Réalise l'Analyse Factorielle et retourne un dictionnaire de résultats sérialisable.
    """
    
    A = X.T @ X
    lambda_vals, U = np.linalg.eigh(A)
    
    # Tri et filtration
    indices_tries = np.argsort(lambda_vals)[::-1]
    lambda_vals = lambda_vals[indices_tries]
    U = U[:, indices_tries]
    mask = lambda_vals > 1e-10
    lambda_vals = lambda_vals[mask]
    U = U[:, mask]
    
    sigma_vals = np.sqrt(lambda_vals)
    
    # Inertie et Rang S
    trace_totale = np.sum(lambda_vals)
    taux_inertie = lambda_vals / trace_totale
    inertie_cumulee = np.cumsum(taux_inertie)
    
    try:
        S = np.where(inertie_cumulee >= seuil_inertie)[0][0] + 1
    except IndexError:
        S = len(lambda_vals)

    F = X @ U
    V = F / sigma_vals.reshape(1, -1)
    
    # Reconstruction
    U_approx = U[:, :S]
    V_approx = V[:, :S]
    Sigma_approx = np.diag(sigma_vals[:S])
    X_approx = V_approx @ Sigma_approx @ U_approx.T
    
    taux_conserve = float(inertie_cumulee[S - 1] * 100) 
    rang_S_python = int(S) # Force S à être un entier Python standard    
    # --- Sérialisation pour JSON (Utilisation des fonctions de formatage) ---
    
    # Valeurs Propres, Taux et Matrice Approchée (Conversion en string/int/fraction)
    lambda_f = [to_fraction_or_int(l) for l in lambda_vals]
    taux_f = [f"{float(t)*100:.2f}%" for t in taux_inertie]
    X_approx_f = np.vectorize(to_fraction_or_int)(X_approx)
    
    # VECTEURS PROPRES : Formatage radical/fractionnaire
    U_display = [format_vector_for_display(U[:, i]) for i in range(U.shape[1])]
    V_display = [format_vector_for_display(V[:, i]) for i in range(V.shape[1])]

    resultats = {
        "valeurs_propres": lambda_f,
        "taux_inertie": taux_f,
        "vecteurs_u": U_display, # Chaînes formatées (radicaux/fractions)
        "vecteurs_v": V_display, # Chaînes formatées (radicaux/fractions)
        "rang_approximation": rang_S_python, # Utiliser l'entier Python standard
        "taux_conserve": f"{taux_conserve:.2f}%", # Utiliser le float Python standard
        "lambda_utilises": lambda_f[:S],
        "matrice_approchee": X_approx_f.tolist()
    }
    
    return resultats

# --- Configuration de l'Application Flask ---
app = Flask(__name__)
CORS(app) # Active CORS

@app.route('/')
def index():
    """Route pour servir la page HTML."""
    return render_template('index.html')

@app.route('/analyse', methods=['POST'])
def run_analyse():
    """Point d'API pour recevoir la matrice et retourner les résultats."""
    try:
        data = request.json
        matrice_list = data.get('matrice')
        
        if not matrice_list or not isinstance(matrice_list, list):
            return jsonify({"error": "Format de matrice invalide."}), 400
        
        X = np.array(matrice_list, dtype=np.float64)
        
        if X.ndim != 2 or X.shape[0] < 1 or X.shape[1] < 1:
            return jsonify({"error": "La matrice doit être 2D et non vide."}), 400
        
        resultats = analyse_factorielle(X)
        
        return jsonify(resultats)
        
    except ValueError as e:
        return jsonify({"error": f"Erreur de format : {e}. Assurez-vous que toutes les valeurs sont numériques."}), 400
    except Exception as e:
        # Erreur générale, incluant LinAlgError
        return jsonify({"error": f"Erreur lors du calcul : {e}. Vérifiez la singularité de la matrice."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
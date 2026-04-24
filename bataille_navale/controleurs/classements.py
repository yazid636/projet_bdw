from model.model_pg import get_classement_ijh, get_classement_cpp

# Récupérer le paramètre delta depuis GET ou utiliser 0 par défaut
delta_raw = GET.get('delta', 0)

if isinstance(delta_raw, list):
    delta_raw = delta_raw[0]

delta_mois = int(delta_raw)

# Récupérer les classements
classement_ijh = get_classement_ijh(SESSION['CONNEXION'], delta_mois)
classement_cpp = get_classement_cpp(SESSION['CONNEXION'], delta_mois)

# Passer les données au template
REQUEST_VARS['classement_ijh'] = classement_ijh
REQUEST_VARS['classement_cpp'] = classement_cpp
REQUEST_VARS['delta_mois'] = delta_mois

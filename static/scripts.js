// Fonction pour formater un seul composant pour l'alignement
function formatComponent(component) {
    // Entoure chaque composant d'un <div> pour que CSS puisse l'aligner
    return `<div class="component-item">${component}</div>`;
}

// Fonction principale de communication avec le backend Flask
async function runAnalysis() {
    const input = document.getElementById('matrix-input').value.trim();
    const errorMessage = document.getElementById('error-message');
    const loading = document.getElementById('loading');
    const resultsContainer = document.getElementById('results-container');
    
    errorMessage.textContent = '';
    resultsContainer.style.display = 'none';
    loading.style.display = 'block';

    const rows = input.split('\n').filter(line => line.trim() !== '');
    const matrix = [];
    
    try {
        rows.forEach(row => {
            const values = row.split(',').map(v => {
                const num = parseFloat(v.trim());
                if (isNaN(num)) throw new Error('Contient une valeur non numérique.');
                return num;
            });
            if (matrix.length > 0 && values.length !== matrix[0].length) {
                 throw new Error('Toutes les lignes n\'ont pas le même nombre de colonnes.');
            }
            if (values.length === 0) throw new Error('Ligne vide.');
            matrix.push(values);
        });

        if (matrix.length < 1 || matrix[0].length < 1) {
            throw new Error('La matrice est vide.');
        }
    } catch (e) {
        loading.style.display = 'none';
        errorMessage.textContent = 'Erreur de saisie : ' + e.message;
        return;
    }

    // Envoi au backend
    try {
        const response = await fetch('/analyse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ matrice: matrix })
        });

        const data = await response.json();

       if (response.ok) {
            try {
                displayResults(data, matrix); // <-- AJOUTER 'matrix' ICI
            } catch (formatError) {
                // Si le serveur a bien répondu (200) mais que l'affichage échoue
                errorMessage.textContent = 'Erreur d\'affichage des résultats (JS) : ' + formatError.message;
                console.error("Erreur de formatage JS:", formatError);
            }
        } else {
            errorMessage.textContent = `Erreur du serveur (${response.status}) : ${data.error || 'Erreur de calcul.'}`;
        }

    } catch (e) {
        // Cette erreur est pour la connexion réseau pure (pas un 200)
        errorMessage.textContent = 'Erreur de connexion au serveur Flask. Assurez-vous que app.py est lancé.';
    } finally {
        loading.style.display = 'none';
    }
}
// Fonction pour afficher les résultats reçus
function displayResults(data,matrix) {
    const eigenTableBody = document.querySelector('#eigen-table tbody');
    const uVectorsPre = document.getElementById('u-vectors');
    const vVectorsPre = document.getElementById('v-vectors');
    const matrixInfoDiv = document.getElementById('matrix-info');
    const approxMatrixPre = document.getElementById('approx-matrix');
    const resultsContainer = document.getElementById('results-container');
    
    eigenTableBody.innerHTML = '';
    
    let cumulativeInertia = 0;

    data.valeurs_propres.forEach((lambda, index) => {
        // Le taux est déjà une chaîne en %
        const tauxStr = data.taux_inertie[index];
        const taux = parseFloat(tauxStr.replace('%', ''));
        cumulativeInertia += taux;
        
        const row = eigenTableBody.insertRow();
        
        // La première ligne du tableau sera formatée pour l'alignement
        row.insertCell().textContent = index + 1;
        row.insertCell().textContent = lambda;
        row.insertCell().textContent = tauxStr;
        row.insertCell().textContent = cumulativeInertia.toFixed(2) + '%';

        if (index < data.rang_approximation) {
            row.classList.add('highlight');
        }
    });
    
    // Affichage des vecteurs u et v avec alignement CSS
    // Les données sont déjà des chaînes formatées, mais elles doivent être divisées pour l'alignement
    uVectorsPre.innerHTML = data.vecteurs_u.map(vectorStr => {
        // Enlever les crochets et diviser par les espaces/virgules/tabs
        const components = vectorStr.slice(1, -1).trim().split(/\s+/); 
        return components.map(formatComponent).join('');
    }).join(''); 

    vVectorsPre.innerHTML = data.vecteurs_v.map(vectorStr => {
        const components = vectorStr.slice(1, -1).trim().split(/\s+/);
        return components.map(formatComponent).join('');
    }).join(''); 

    // Affichage des informations sur la matrice
    matrixInfoDiv.innerHTML = `
        <p><strong>Rang d'approximation (S) choisi :</strong> ${data.rang_approximation}</p>
        <p><strong>Taux d'information conservé :</strong> ${data.taux_conserve} (Seuil demandé : 60%)</p>
        <p><strong>Valeurs propres utilisées :</strong> [${data.lambda_utilises.join(', ')}]</p>
    `;
    
    // Affichage de la Matrice Approchée avec alignement CSS
    approxMatrixPre.innerHTML = data.matrice_approchee.map(row => 
        row.map(formatComponent).join('')
    ).join('');

   // ...
    // Ajuster le nombre de colonnes dans la grille CSS pour les vecteurs et la matrice
    if (data.vecteurs_u.length > 0) {
        // U est le nombre de variables (colonnes de X)
        const numColsU = matrix[0].length; // <-- ERREUR ICI (matrix n'est pas visible)
        document.getElementById('u-vectors').style.gridTemplateColumns = `repeat(${numColsU}, max-content)`;
        document.getElementById('approx-matrix').style.gridTemplateColumns = `repeat(${numColsU}, max-content)`;
    }
    if (data.vecteurs_v.length > 0) {
        // V est le nombre d'individus (lignes de X)
        const numColsV = matrix.length; // <-- ERREUR ICI (matrix n'est pas visible)
        document.getElementById('v-vectors').style.gridTemplateColumns = `repeat(${numColsV}, max-content)`;
    }
    // ...

    resultsContainer.style.display = 'block';
    window.scrollTo(0, document.body.scrollHeight);
}
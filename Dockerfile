# 1. Image de base
FROM python:3.11-slim

# 2. Création utilisateur (Placé en haut pour la clarté, c'est très bien)
RUN useradd -m -u 1000 ecoarch

# 3. Installation Système Complète
# Ajout de git, unzip, gnupg et ca-certificates pour la robustesse
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    gnupg \
    ca-certificates \
    # Installation Node.js 20 LTS (Script officiel)
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    # Installation Infracost
    && curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh \
    # Nettoyage drastique (cache apt + listes)
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Dossier de travail
WORKDIR /app

# 5. Dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copie optimisée (C'est parfait)
# Les fichiers sont copiés et appartiennent directement à ecoarch
# Zéro duplication de données dans les couches Docker
COPY --chown=ecoarch:ecoarch . .

# 6. Copie du code source complet
COPY --chown=ecoarch:ecoarch . .

# Puisque rxconfig.py est dans le dossier 'frontend', on définit
# le dossier de travail final à l'intérieur de ce sous-dossier.
WORKDIR /app/frontend

# 7. Bascule sur l'utilisateur sécurisé
USER ecoarch

# 8. Exposition des ports
EXPOSE 3000
EXPOSE 8000

# 9. Démarrage
CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
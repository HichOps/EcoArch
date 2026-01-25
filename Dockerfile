# 1. Image de base
FROM python:3.11-slim

# 2. Création utilisateur
RUN useradd -m -u 1000 ecoarch

# 3. Installation Système Complète (Node.js + Infracost + TERRAFORM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    unzip \
    gnupg \
    lsb-release \
    ca-certificates \
    # A. Installation Node.js 20 LTS
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    # B. Installation Terraform (NOUVEAU)
    && curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update && apt-get install -y terraform \
    # C. Installation Infracost
    && curl -fsSL https://raw.githubusercontent.com/infracost/infracost/master/scripts/install.sh | sh \
    # D. Nettoyage
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Dossier de travail
WORKDIR /app

# 5. Dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copie optimisée
COPY --chown=ecoarch:ecoarch . .

# 7. Sécurité
USER ecoarch

# 8. Exposition
EXPOSE 3000
EXPOSE 8000

# On change de dossier pour entrer dans le dossier du frontend
# C'est là que se trouve rxconfig.py
WORKDIR /app/frontend

# 9. Démarrage
CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
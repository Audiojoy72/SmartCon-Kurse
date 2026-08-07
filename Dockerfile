# SmartCon-Schulungen — App-Image
# Enthält die App plus alle Werkzeuge, die der Agent braucht:
# claude- & kimi-CLI (Headless-Agenten), higgsfield-CLI (Video/Bild/Voiceover),
# ffmpeg, Node 22 (HyperFrames), cloudflared + openssh (Transkriptions-Tunnel).
#
# Anmeldungen kommen NICHT ins Image — sie werden als Volumes gemountet:
#   ~/.claude, ~/.kimi-code, ~/.config/higgsfield, ~/.ssh, ~/.cloudflare
# siehe docker-compose.yml.

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/root/.local/bin:/root/.kimi-code/bin:${PATH}"

# Systempakete: ffmpeg (Muxing), curl/ca-certificates (Installer),
# openssh-client (Tunnel zum Transkriptionsdienst), git (Agent-Workflows),
# libreoffice-impress + poppler-utils (PPTX → PDF → PNG für Deck-QA und
# den Produktionspfad „Folien einbetten")
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl ca-certificates openssh-client git gnupg \
        libreoffice-impress poppler-utils fonts-inter \
    && rm -rf /var/lib/apt/lists/*

# cloudflared (Cloudflare Access / SSH-Tunnel)
RUN curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
        -o /tmp/cloudflared.deb \
    && dpkg -i /tmp/cloudflared.deb && rm /tmp/cloudflared.deb

# Node 22 (HyperFrames-Renderings)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Higgsfield-CLI (Paketname im npm-Registry: @higgsfield/cli)
RUN npm i -g @higgsfield/cli

# Agenten-CLIs (Headless-Backends). Anmeldung erfolgt über gemountete Volumes.
RUN curl -fsSL https://claude.ai/install.sh | bash
RUN curl -fsSL https://code.kimi.com/install.sh | bash

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY static/ static/
COPY skill/ skill/
COPY README.md SPEC.md ./

EXPOSE 8710
CMD ["python", "-m", "app.main"]

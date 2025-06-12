# マルチステージビルドでサイズ削減
FROM python:3.13-slim as builder

WORKDIR /app
COPY pyproject.toml ./

# 依存関係をインストールするためのrequirements.txtを生成
RUN pip install --no-cache-dir pip-tools && \
    pip-compile --output-file=requirements.txt pyproject.toml

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt --target=/app/site-packages

FROM python:3.13-slim
WORKDIR /app

# Node.jsとnpmをインストール
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Node.jsとnpmのバージョンを確認
RUN node -v && npm -v

# builderステージからサイトパッケージをコピー
COPY --from=builder /app/site-packages /usr/local/lib/python3.13/site-packages

# アプリケーションファイルをコピー
COPY . .

# 動作確認用のコマンド
RUN echo "Installed packages:" && \
    pip list && \
    echo "Checking for uvicorn:" && \
    which uvicorn || echo "uvicorn command not found, checking if module exists:" && \
    python -c "import uvicorn; print(f'uvicorn module found at {uvicorn.__file__}')" || echo "uvicorn module not found" && \
    echo "Checking for npx:" && \
    which npx || echo "npx command not found"

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

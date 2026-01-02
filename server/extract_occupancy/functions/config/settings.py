import os

from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

# 環境変数の取得
REGION = os.getenv("REGION", "asia-northeast1")
BUCKET = os.getenv("BUCKET", None)

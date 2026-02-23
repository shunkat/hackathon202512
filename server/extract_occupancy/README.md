# Extract Occupancy

画像から混雑状況(空席数/空じゃない席数/混雑度)を抽出するfunctions

## 環境構築手順

```zsh
cd server/extract_occupancy/functions
uv venv venv
source venv/bin/activate
uv pip install -r requirements.txt
```

新たに依存関係を追加した場合
```zsh
uv pip sync requirements.txt --python venv/bin/python
```

## 開発用起動手順

```zsh
firebase emulators:start
```

## テスト手順

test配下で実行

## notebooks

```zsh
uv run python -m ipykernel install --user --name extract-occupancy --display-name "Python312 (extract-occupancy)"
```
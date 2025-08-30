# 🌍 Translate a Document into Every Language (Google Cloud Translation v3)

This tool takes a text document and automatically translates it into **all languages supported by Google Cloud Translation**.  
It detects the source language, fetches the list of supported target languages dynamically, and saves one output file per language.  
Live progress is shown as translations complete.

---

## ✨ Features
- ✅ Detects the source language automatically  
- ✅ Translates into **all available languages** from the API  
- ✅ Saves results as `basename.LANG.txt` in your output folder  
- ✅ Concurrent translation (fast) with live progress feedback  
- ✅ Skip languages with `--exclude`  

---

## 🚀 Requirements

- Python **3.9+**
- A Google Cloud project with:
  - **Translation API v3** enabled  
  - A service account with credentials JSON  

### Install dependencies
```bash
pip install google-cloud-translate
```

### Authenticate
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

---

## 🔧 Usage

```bash
python translate_all.py \
  --project YOUR_PROJECT_ID \
  --input /path/to/input.txt \
  --outdir translations_out
```

### Options
- `--project` – Google Cloud project ID (**required**)  
- `--input` – Path to your input text file (**required**)  
- `--outdir` – Directory to write translated files (default: `translations_out`)  
- `--exclude` – Comma-separated list of language codes to skip (e.g. `en,fr,ja`)  
- `--workers` – Number of concurrent translation threads (default: `8`)  

---

## 📂 Output

If your input is `document.txt` and you translated into French (`fr`) and Japanese (`ja`),  
the output folder will contain:

```
translations_out/
├── document.fr.txt
├── document.ja.txt
```

Each file contains the full translated text.

---

## ⚠️ Notes

- **Costs**: Each target language incurs translation charges. Check [Google Cloud Translation pricing](https://cloud.google.com/translate/pricing).  
- **Text size**: Long texts are automatically split into safe chunks before translation.  
- **Formats**: Only plain text is handled by default. To translate HTML, set `mime_type="text/html"` in the script.  
- **Errors**: Some rare languages may fail due to model availability. The script reports failed cases at the end.  

---

## 🛠 Example

```bash
python translate_all.py \
  --project my-gcp-project \
  --input article.txt \
  --outdir ./all_languages \
  --exclude en,es \
  --workers 16
```

Output:
```
Detected source language: en
Found 135 supported languages; translating into 133 targets.
[1/133] ✅ fr (French)
[2/133] ✅ de (German)
[3/133] ✅ ja (Japanese)
...
Done.
All languages translated successfully.
```

---

## 📜 License
MIT – use freely, but be mindful of API usage limits and billing.

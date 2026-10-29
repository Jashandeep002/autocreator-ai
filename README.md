# AutoCreator AI — iPhone cloud edition

A free-first Streamlit web app. Paste a script and generate a portrait MP4, research trends via search links, and manually track publishing.

## Deploy entirely from iPhone (Safari)

1. Download and unzip `AutoCreator_AI_iPhone_Cloud.zip` in the iPhone **Files** app. The extracted folder contains `app.py`, `requirements.txt`, `runtime.txt`, `.gitignore`, and `.streamlit/config.toml`.
2. Visit **github.com** in Safari and create a free account (or sign in). Create a **new public repository** named `autocreator-ai` (public repositories are required for the typical free Streamlit Community Cloud workflow). Do **not** put passwords, API keys, or private scripts in the repository.
3. Open the new repo, tap **Add file → Upload files**. Choose `app.py`, `requirements.txt`, `runtime.txt`, and optionally `README.md` from the unzipped folder, then commit. If uploading several files is awkward on mobile, do them one at a time. The `.streamlit/config.toml` file is optional; you can omit it. If controls are missing, Safari's **aA → Request Desktop Website** may help.
4. Visit **share.streamlit.io** in Safari, sign in using GitHub, and choose **Create app → Deploy a public app from GitHub** (wording may vary).
5. Select your GitHub repository and branch `main`, and set the main file path to **`app.py`**. Choose an app URL and deploy. Wait for dependencies to install; this may take several minutes.
6. Open the provided `*.streamlit.app` URL on your iPhone. In Safari tap **Share → Add to Home Screen** to make it behave like an app icon.
7. In **Create video**, paste a script, tap **Generate MP4**, then **Download MP4**. Save the file to Files or Photos and upload it to your accounts manually.

## Limitations and privacy

- Free Streamlit Community Cloud may sleep, throttle, change quotas, or be unavailable for some accounts; deployment is not guaranteed.
- **Generated videos, database entries, and publishing history are stored on ephemeral cloud storage. They can disappear after restarts/redeploys. Download videos immediately.** This is a demonstration, not durable hosted storage.
- This version renders text-scene MP4s only. No voiceover, licensed footage acquisition, AI imagery, automatic posting, live trend scraping, or earnings API integration.
- The public repository exposes the code, not your scripts typed into the running app. However, the hosted app URL is publicly reachable unless access controls are added. Do not enter confidential scripts or sensitive data.
- Free hosting CPU/RAM limits can cause long scripts to fail; start with 3 short sentences and 10–20 seconds.
- Do not use copyrighted or misleading content without permission. Follow platform monetization policies.

## Local development (optional)

`python -m pip install -r requirements.txt`

`python -m streamlit run app.py`

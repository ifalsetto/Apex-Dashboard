# OpenAI Platform setup

The AI Coach page reads your OpenAI API credential from Streamlit secrets first, then from environment variables.

## Local setup

Create a private file named `.streamlit/secrets.toml` on your own machine.

Add your OpenAI Platform credential under the variable name `OPENAI_API_KEY`.

Do not commit the private secrets file.

## Streamlit Cloud setup

Add the same variable name in the Streamlit Cloud app secrets panel.

## Run

```bash
pip install -r requirements.txt
streamlit run apex_dashboard.py
```

Then open the page named `FalseTech Apex AI Coach` from the Streamlit sidebar.
